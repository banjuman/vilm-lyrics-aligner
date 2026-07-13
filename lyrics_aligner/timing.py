

from __future__ import annotations

from collections.abc import Sequence

from .models import Cue
from .timing_core import VocalActivity
from .timing_core import polish_singing_cue_times as _polish_singing_cue_times


def polish_singing_cue_times(
    cues: Sequence[Cue],
    *,
    activity: VocalActivity | None = None,
    lead_ms: int = 0,
    end_hold_ms: int = 500,
    min_duration_ms: int = 500,
    max_duration_ms: int = 10000,
    min_gap_ms: int = 80,
) -> list[Cue]:
    """Resolve overlapping raw alignments, then apply singing timing policy."""
    bounded: list[Cue] = []
    for index, cue in enumerate(cues):
        end = cue.end
        if index + 1 < len(cues) and end > cues[index + 1].start:
            # A single subtitle lane cannot faithfully show two overlapping
            # source lines. Switch at the next detected line instead of
            # protecting a clearly overlong/structurally conflicting end.
            end = max(cue.start, cues[index + 1].start)
        bounded.append(Cue(text=cue.text, start=cue.start, end=end))
    return _polish_singing_cue_times(
        bounded,
        activity=activity,
        lead_ms=lead_ms,
        end_hold_ms=end_hold_ms,
        min_duration_ms=min_duration_ms,
        max_duration_ms=max_duration_ms,
        min_gap_ms=min_gap_ms,
    )


__all__ = ["VocalActivity", "polish_singing_cue_times"]
