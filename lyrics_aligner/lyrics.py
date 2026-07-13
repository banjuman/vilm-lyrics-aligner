
from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from .models import AlignmentUnit, Cue

_BREAK_AFTER = set(",.!?;:，。！？；：…~、)]}〉》」』")


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", line)).strip()


def split_lyrics(text: str, max_chars: int = 30) -> list[str]:
    """Preserve source lines and split only lines longer than max_chars."""
    if max_chars < 1:
        raise ValueError("max_chars must be at least 1")

    cues: list[str] = []
    for raw_line in text.splitlines():
        line = normalize_line(raw_line)
        if not line:
            continue
        cues.extend(_split_line(line, max_chars))
    return cues


def split_lyrics_with_paragraph_barriers(
    text: str, max_chars: int = 30
) -> tuple[list[str], set[int]]:
    """Split lyrics while retaining blank-stanza boundaries for auto mode."""
    if max_chars < 1:
        raise ValueError("max_chars must be at least 1")
    cues: list[str] = []
    barriers: set[int] = set()
    saw_blank = False
    for raw_line in text.splitlines():
        line = normalize_line(raw_line)
        if not line:
            if cues:
                saw_blank = True
            continue
        if saw_blank and cues:
            barriers.add(len(cues))
        cues.extend(_split_line(line, max_chars))
        saw_blank = False
    return cues, barriers


def _split_line(line: str, max_chars: int) -> list[str]:
    parts: list[str] = []
    remaining = line
    while len(remaining) > max_chars:
        cut = _best_cut(remaining, max_chars)
        part = remaining[:cut].strip()
        if not part:
            cut = max_chars
            part = remaining[:cut].strip()
        parts.append(part)
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return parts


def _best_cut(text: str, max_chars: int) -> int:
    lower = max(1, int(max_chars * 0.55))
    candidates: list[tuple[int, int]] = []
    for index in range(lower, min(max_chars, len(text) - 1) + 1):
        before = text[index - 1]
        after = text[index] if index < len(text) else ""
        if before in _BREAK_AFTER:
            priority = 3
        elif before.isspace():
            priority = 2
        elif after.isspace():
            priority = 1
        else:
            continue
        candidates.append((priority, index))
    if not candidates:
        return max_chars
    best_priority = max(priority for priority, _ in candidates)
    return max(index for priority, index in candidates if priority == best_priority)


def alignment_text(cue_texts: Sequence[str]) -> str:
    return " ".join(normalize_line(text) for text in cue_texts if normalize_line(text))


def _match_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(char for char in normalized if char.isalnum())


def map_units_to_cues(
    cue_texts: Sequence[str],
    units: Sequence[AlignmentUnit],
) -> list[Cue]:
    """Map sequential word/character timestamps back to source cue boundaries."""
    if not cue_texts:
        return []
    if not units:
        raise ValueError("The aligner returned no timestamp units")

    cue_keys = [_match_key(text) for text in cue_texts]
    if any(not key for key in cue_keys):
        raise ValueError("A cue contains no alignable letters or numbers")
    target = "".join(cue_keys)
    boundaries: list[tuple[int, int]] = []
    cursor = 0
    for key in cue_keys:
        boundaries.append((cursor, cursor + len(key)))
        cursor += len(key)

    timed_spans: list[tuple[int, int, float, float]] = []
    cursor = 0
    for unit in units:
        key = _match_key(unit.text)
        if not key:
            continue
        position = target.find(key, cursor)
        if position < 0:
            lookahead_end = min(len(target), cursor + max(64, len(key) * 4))
            position = target.find(key, max(0, cursor - 4), lookahead_end)
        if position < 0:
            raise ValueError(
                f"Could not map aligner output {unit.text!r} near lyric offset {cursor}. "
                "The performed lyrics may differ from the supplied text."
            )
        end_position = position + len(key)
        timed_spans.append((position, end_position, unit.start, unit.end))
        cursor = end_position

    if not timed_spans:
        raise ValueError("The aligner returned no usable text timestamps")

    cues: list[Cue] = []
    for text, (cue_start, cue_end) in zip(cue_texts, boundaries):
        overlaps: list[tuple[float, float]] = []
        for span_start, span_end, time_start, time_end in timed_spans:
            overlap_start = max(cue_start, span_start)
            overlap_end = min(cue_end, span_end)
            if overlap_start >= overlap_end:
                continue
            span_width = span_end - span_start
            if span_width <= 0:
                continue
            duration = time_end - time_start
            relative_start = (overlap_start - span_start) / span_width
            relative_end = (overlap_end - span_start) / span_width
            overlaps.append(
                (
                    time_start + duration * relative_start,
                    time_start + duration * relative_end,
                )
            )
        if not overlaps:
            raise ValueError(f"No timestamps were mapped to cue: {text!r}")
        cues.append(Cue(text=text, start=overlaps[0][0], end=overlaps[-1][1]))
    return cues


def polish_cue_times(
    cues: Sequence[Cue],
    lead_ms: int = 80,
    end_pad_ms: int = 300,
    min_duration_ms: int = 500,
    min_gap_ms: int = 20,
) -> list[Cue]:
    if not cues:
        return []
    lead = max(0, lead_ms) / 1000
    pad = max(0, end_pad_ms) / 1000
    minimum = max(0, min_duration_ms) / 1000
    gap = max(0, min_gap_ms) / 1000

    result: list[Cue] = []
    for index, cue in enumerate(cues):
        start = max(0.0, cue.start - lead)
        end = max(cue.end + pad, start + minimum)
        if index + 1 < len(cues):
            next_start = max(0.0, cues[index + 1].start - lead)
            end = min(end, max(start, next_start - gap))
        result.append(Cue(text=cue.text, start=start, end=end))
    return result
