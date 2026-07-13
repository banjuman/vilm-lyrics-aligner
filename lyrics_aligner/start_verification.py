from __future__ import annotations

from dataclasses import dataclass

from .matching import CueTranscriptMatch
from .models import Cue


@dataclass(frozen=True)
class StartAdjustment:
    cue_index: int
    kind: str
    original_start: float
    refined_start: float
    transcript_start: float | None
    previous_transcript_end: float | None
    local_start: float | None
    global_start: float | None
    local_end: float | None
    global_end: float | None


def refine_start_from_evidence(
    cue_index: int,
    cue: Cue,
    match: CueTranscriptMatch,
    *,
    previous_match: CueTranscriptMatch | None = None,
    local_cue: Cue | None = None,
    global_cue: Cue | None = None,
) -> tuple[Cue, list[StartAdjustment]]:
    """Refine a lyric start only when independent timing evidence agrees.

    ASR provides a lexical floor when its text match is strong.  A second,
    deliberately stricter rule handles a common singing boundary failure:
    local/ASR timing attaches the next lyric to a preceding sustained vowel,
    while full-song forced alignment finds a later start but nearly the same
    phrase end.  End agreement distinguishes a false leading attachment from
    a cue whose whole alignment simply shifted.
    """

    original_start = cue.start
    refined = cue
    adjustments: list[StartAdjustment] = []

    if _strong_lexical_match(match) and cue.start < float(match.start) - 0.12:
        refined_start = max(cue.start, float(match.start) - 0.05)
        refined = Cue(cue.text, refined_start, max(refined_start, cue.end))
        adjustments.append(
            _adjustment(
                cue_index,
                "lexical_floor",
                original_start,
                refined_start,
                match,
                previous_match,
                local_cue,
                global_cue,
            )
        )

    if _sustained_boundary_consensus(
        refined,
        match,
        previous_match=previous_match,
        local_cue=local_cue,
        global_cue=global_cue,
    ):
        refined_start = max(refined.start, float(global_cue.start))
        refined = Cue(refined.text, refined_start, max(refined_start, refined.end))
        adjustments.append(
            _adjustment(
                cue_index,
                "sustained_boundary_consensus",
                original_start,
                refined_start,
                match,
                previous_match,
                local_cue,
                global_cue,
            )
        )

    return refined, adjustments


def _strong_lexical_match(match: CueTranscriptMatch | None) -> bool:
    return bool(
        match is not None
        and match.start is not None
        and match.end is not None
        and match.exact_characters >= 2
        and match.similarity >= 0.62
        and match.coverage >= 0.45
    )


def _sustained_boundary_consensus(
    cue: Cue,
    match: CueTranscriptMatch,
    *,
    previous_match: CueTranscriptMatch | None,
    local_cue: Cue | None,
    global_cue: Cue | None,
) -> bool:
    if (
        not _strong_lexical_match(match)
        or not _strong_lexical_match(previous_match)
        or local_cue is None
        or global_cue is None
        or previous_match is None
        or previous_match.end is None
        or match.start is None
    ):
        return False

    # Singing transitions may be legato or have only a short breath. Longer
    # gaps are ordinary separate phrases and do not need this safeguard.
    transcript_gap = float(match.start) - float(previous_match.end)
    if not -0.08 <= transcript_gap <= 0.65:
        return False

    later_start = global_cue.start - cue.start
    if not 0.30 <= later_start <= 2.25:
        return False

    # Both alignments must agree on where the phrase finishes. If both start
    # and end moved together, this is general drift rather than a swallowed
    # sustain and the conservative choice is to leave it unchanged.
    if abs(global_cue.end - local_cue.end) > 0.75:
        return False
    if global_cue.start >= cue.end or global_cue.end - global_cue.start < 0.35:
        return False

    return True


def _adjustment(
    cue_index: int,
    kind: str,
    original_start: float,
    refined_start: float,
    match: CueTranscriptMatch,
    previous_match: CueTranscriptMatch | None,
    local_cue: Cue | None,
    global_cue: Cue | None,
) -> StartAdjustment:
    return StartAdjustment(
        cue_index=cue_index,
        kind=kind,
        original_start=original_start,
        refined_start=refined_start,
        transcript_start=match.start,
        previous_transcript_end=(
            previous_match.end if previous_match is not None else None
        ),
        local_start=local_cue.start if local_cue is not None else None,
        global_start=global_cue.start if global_cue is not None else None,
        local_end=local_cue.end if local_cue is not None else None,
        global_end=global_cue.end if global_cue is not None else None,
    )
