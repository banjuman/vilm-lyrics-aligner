from __future__ import annotations

from collections.abc import Sequence

from .matching import normalize_for_match
from .models import AlignmentUnit, Cue


def map_units_to_optional_cues(
    cue_texts: Sequence[str], units: Sequence[AlignmentUnit]
) -> list[Cue | None]:
    """Map supplied-text alignment units while tolerating failed tail lines."""
    keys = [normalize_for_match(text) for text in cue_texts]
    target = "".join(keys)
    boundaries: list[tuple[int, int]] = []
    cursor = 0
    for key in keys:
        boundaries.append((cursor, cursor + len(key)))
        cursor += len(key)

    spans: list[tuple[int, int, float, float]] = []
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
        spans.append((position, position + len(key), unit.start, unit.end))
        cursor = position + len(key)

    result: list[Cue | None] = []
    for text, (cue_start, cue_end) in zip(cue_texts, boundaries):
        overlaps: list[tuple[float, float]] = []
        for span_start, span_end, time_start, time_end in spans:
            overlap_start = max(cue_start, span_start)
            overlap_end = min(cue_end, span_end)
            if overlap_start >= overlap_end or span_end <= span_start:
                continue
            width = span_end - span_start
            duration = time_end - time_start
            overlaps.append(
                (
                    time_start + duration * (overlap_start - span_start) / width,
                    time_start + duration * (overlap_end - span_start) / width,
                )
            )
        result.append(
            Cue(text=text, start=overlaps[0][0], end=overlaps[-1][1])
            if overlaps
            else None
        )
    return result
