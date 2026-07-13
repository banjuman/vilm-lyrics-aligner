



from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from typing import Mapping, Sequence

from .matching import normalize_for_match
from .models import AlignmentUnit, Cue


@dataclass(frozen=True)
class _TimedWord:
    text: str
    start: float
    end: float


def map_units_to_source_lines(
    cue_texts: Sequence[str], units: Sequence[AlignmentUnit]
) -> dict[int, list[AlignmentUnit]]:
    """Assign forced-alignment units to source lines by normalized text order."""
    line_keys = [normalize_for_match(text) for text in cue_texts]
    target = "".join(line_keys)
    boundaries: list[tuple[int, int]] = []
    cursor = 0
    for key in line_keys:
        boundaries.append((cursor, cursor + len(key)))
        cursor += len(key)

    result = {index: [] for index in range(len(cue_texts))}
    cursor = 0
    for unit in units:
        key = normalize_for_match(unit.text)
        if not key:
            continue
        position = target.find(key, cursor)
        if position < 0:
            position = target.find(
                key, max(0, cursor - 4), min(len(target), cursor + max(64, len(key) * 4))
            )
        if position < 0:
            continue
        unit_end = position + len(key)
        overlaps = [
            (max(position, start), min(unit_end, end), index)
            for index, (start, end) in enumerate(boundaries)
            if max(position, start) < min(unit_end, end)
        ]
        if overlaps:
            owner = max(overlaps, key=lambda item: item[1] - item[0])[2]
            result[owner].append(unit)
        cursor = max(cursor, unit_end)
    return result


def auto_segment_source_cues(
    cue_texts: Sequence[str],
    cues_by_index: Mapping[int, Cue],
    global_units: Sequence[AlignmentUnit],
    *,
    local_units_by_index: Mapping[int, Sequence[AlignmentUnit]] | None = None,
    global_pause_indices: set[int] | None = None,
    preferred_chars: int = 30,
    hard_chars: int = 50,
    minimum_internal_gap: float = 1.7,
    target_duration: float = 5.8,
) -> dict[int, list[Cue]]:
    """Split each aligned source line using its local pace and sung pauses.

    Source newlines are strong boundaries. Dense continuous rap lines may use
    the hard character allowance, while slower or internally paused lines are
    split at timed word boundaries. A separate conservative pass may repair an
    obvious display-width wrap, but never crosses a blank stanza.
    """
    if preferred_chars < 1 or hard_chars < preferred_chars:
        raise ValueError("Expected 1 <= preferred_chars <= hard_chars")
    line_units = map_units_to_source_lines(cue_texts, global_units)
    local_units_by_index = local_units_by_index or {}
    global_pause_indices = global_pause_indices or set()
    result: dict[int, list[Cue]] = {}
    for index, cue in cues_by_index.items():
        global_evidence = list(line_units.get(index) or [])
        local_evidence = list(local_units_by_index.get(index) or [])
        units = local_evidence or global_evidence
        evidence_cue = cue
        # Batched local alignment can compress a long sung pause into a
        # continuous phrase. Preserve a clear pause found by the full-song
        # alignment when the local window contains no comparable gap.
        if (
            index in global_pause_indices
            and len(global_evidence) >= 2
            and _largest_unit_gap(global_evidence) >= minimum_internal_gap
            and _largest_unit_gap(local_evidence) < 1.0
        ):
            units = global_evidence
            evidence_cue = Cue(
                cue.text,
                global_evidence[0].start,
                global_evidence[-1].end,
            )
        result[index] = _segment_line(
            evidence_cue,
            units,
            preferred_chars=preferred_chars,
            hard_chars=hard_chars,
            minimum_internal_gap=minimum_internal_gap,
            target_duration=target_duration,
        )
    return result


def merge_obvious_wrapped_lines(
    cue_texts: Sequence[str],
    segmented: Mapping[int, Sequence[Cue]],
    *,
    paragraph_barriers: set[int] | None = None,
    preferred_chars: int = 30,
    maximum_gap: float = 0.15,
) -> tuple[dict[int, list[Cue]], int]:
    """Merge only a likely display-width wrap in automatic mode.

    Short lyric lines remain separate. A merge requires near-continuous timing,
    no sentence-ending punctuation, a readable combined length, and at least
    one line long enough to look like an accidental visual wrap.
    """
    barriers = paragraph_barriers or set()
    result = {index: list(items) for index, items in segmented.items()}
    merged_count = 0
    index = 0
    minimum_wrapped_length = max(12, round(preferred_chars * 0.65))
    sentence_end = ".!?;:。！？；：…"
    while index + 1 < len(cue_texts):
        left_items = result.get(index, [])
        right_items = result.get(index + 1, [])
        if (
            index + 1 not in barriers
            and len(left_items) == 1
            and len(right_items) == 1
        ):
            left = left_items[0]
            right = right_items[0]
            gap = right.start - left.end
            combined = f"{left.text} {right.text}".strip()
            if (
                -0.05 <= gap <= maximum_gap
                and left.text[-1:] not in sentence_end
                and len(combined) <= preferred_chars
                and max(
                    len(normalize_for_match(left.text)),
                    len(normalize_for_match(right.text)),
                )
                >= minimum_wrapped_length
            ):
                result[index] = [
                    Cue(combined, left.start, max(left.end, right.end))
                ]
                result[index + 1] = []
                merged_count += 1
                index += 2
                continue
        index += 1
    return result, merged_count


def _largest_unit_gap(units: Sequence[AlignmentUnit]) -> float:
    return max(
        (max(0.0, right.start - left.end) for left, right in zip(units, units[1:])),
        default=0.0,
    )


def _segment_line(
    cue: Cue,
    units: Sequence[AlignmentUnit],
    *,
    preferred_chars: int,
    hard_chars: int,
    minimum_internal_gap: float,
    target_duration: float,
) -> list[Cue]:
    words = _timed_words(cue, units)
    if len(words) < 2:
        return [cue]

    gaps = [max(0.0, right.start - left.end) for left, right in zip(words, words[1:])]
    positive = [gap for gap in gaps if gap > 0.02]
    # A single large pause is evidence, not the song's normal word spacing.
    # Estimate typical spacing only when there are enough observations.
    typical_gap = statistics.median(positive) if len(positive) >= 3 else 0.0
    long_gap = max(minimum_internal_gap, min(2.2, typical_gap * 4.0))
    punctuation_gap = min(long_gap, 1.2)

    forced = [
        index + 1
        for index, gap in enumerate(gaps)
        if gap >= long_gap
        or (
            gap >= punctuation_gap
            and words[index].text[-1:] in ".!?;:。！？；：…"
        )
    ]
    ranges: list[tuple[int, int]] = []
    start = 0
    for boundary in forced:
        ranges.append((start, boundary))
        start = boundary
    ranges.append((start, len(words)))

    refined: list[tuple[int, int]] = []
    for first, last in ranges:
        refined.extend(
            _split_range(
                words,
                first,
                last,
                preferred_chars=preferred_chars,
                hard_chars=hard_chars,
                target_duration=target_duration,
                long_gap=long_gap,
            )
        )
    if len(refined) == 1:
        return [cue]

    segments: list[Cue] = []
    for position, (first, last) in enumerate(refined):
        text = " ".join(word.text for word in words[first:last]).strip()
        start_time = cue.start if position == 0 else max(cue.start, words[first].start)
        end_time = cue.end if position == len(refined) - 1 else min(cue.end, words[last - 1].end)
        if end_time < start_time:
            end_time = start_time
        segments.append(Cue(text=text, start=start_time, end=end_time))
    return segments


def _split_range(
    words: Sequence[_TimedWord],
    first: int,
    last: int,
    *,
    preferred_chars: int,
    hard_chars: int,
    target_duration: float,
    long_gap: float,
) -> list[tuple[int, int]]:
    if last - first < 2:
        return [(first, last)]
    text = " ".join(word.text for word in words[first:last])
    alignable_chars = len(normalize_for_match(text))
    duration = max(0.01, words[last - 1].end - words[first].start)
    rate = alignable_chars / duration
    if rate <= 4.0:
        dynamic_limit = preferred_chars
    elif rate >= 7.0:
        dynamic_limit = hard_chars
    else:
        ratio = (rate - 4.0) / 3.0
        dynamic_limit = round(preferred_chars + (hard_chars - preferred_chars) * ratio)

    too_long = len(text) > dynamic_limit
    too_slow = (
        duration > target_duration
        and alignable_chars >= max(18, round(preferred_chars * 0.6))
        and rate < 6.5
    )
    if not too_long and not too_slow:
        return [(first, last)]

    total_chars = max(1, len(text))
    total_duration = max(0.01, words[last - 1].end - words[first].start)
    candidates: list[tuple[float, int]] = []
    for boundary in range(first + 1, last):
        left_text = " ".join(word.text for word in words[first:boundary])
        right_text = " ".join(word.text for word in words[boundary:last])
        if not left_text or not right_text:
            continue
        char_balance = abs(len(left_text) / total_chars - 0.5)
        time_position = (words[boundary].start - words[first].start) / total_duration
        time_balance = abs(time_position - 0.5)
        gap = max(0.0, words[boundary].start - words[boundary - 1].end)
        punctuation_bonus = 0.18 if words[boundary - 1].text[-1:] in ",.!?;:，。！？；：…" else 0.0
        gap_bonus = min(0.35, gap / max(long_gap, 0.1) * 0.35)
        tiny_penalty = 0.5 if min(len(left_text), len(right_text)) < 3 else 0.0
        score = char_balance * 0.65 + time_balance * 0.35 + tiny_penalty
        score -= punctuation_bonus + gap_bonus
        candidates.append((score, boundary))
    if not candidates:
        return [(first, last)]
    _, boundary = min(candidates)
    return _split_range(
        words,
        first,
        boundary,
        preferred_chars=preferred_chars,
        hard_chars=hard_chars,
        target_duration=target_duration,
        long_gap=long_gap,
    ) + _split_range(
        words,
        boundary,
        last,
        preferred_chars=preferred_chars,
        hard_chars=hard_chars,
        target_duration=target_duration,
        long_gap=long_gap,
    )


def _timed_words(cue: Cue, units: Sequence[AlignmentUnit]) -> list[_TimedWord]:
    tokens = [token for token in re.findall(r"\S+", cue.text) if normalize_for_match(token)]
    if len(tokens) < 2 or not units:
        return []
    token_keys = [normalize_for_match(token) for token in tokens]
    line_key = "".join(token_keys)
    token_spans: list[tuple[int, int]] = []
    cursor = 0
    for key in token_keys:
        token_spans.append((cursor, cursor + len(key)))
        cursor += len(key)

    unit_spans: list[tuple[int, int, AlignmentUnit]] = []
    cursor = 0
    for unit in units:
        key = normalize_for_match(unit.text)
        if not key:
            continue
        position = line_key.find(key, cursor)
        if position < 0:
            position = line_key.find(key, max(0, cursor - 3))
        if position < 0:
            continue
        unit_spans.append((position, position + len(key), unit))
        cursor = max(cursor, position + len(key))

    result: list[_TimedWord] = []
    for token, (token_start, token_end) in zip(tokens, token_spans):
        times: list[tuple[float, float]] = []
        for unit_start, unit_end, unit in unit_spans:
            overlap_start = max(token_start, unit_start)
            overlap_end = min(token_end, unit_end)
            if overlap_start >= overlap_end:
                continue
            width = unit_end - unit_start
            duration = max(0.0, unit.end - unit.start)
            relative_start = (overlap_start - unit_start) / width
            relative_end = (overlap_end - unit_start) / width
            times.append(
                (
                    unit.start + duration * relative_start,
                    unit.start + duration * relative_end,
                )
            )
        if not times:
            return []
        result.append(
            _TimedWord(
                token,
                max(cue.start, times[0][0]),
                min(cue.end, times[-1][1]),
            )
        )
    return result
