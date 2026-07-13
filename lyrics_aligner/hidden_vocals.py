from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .matching import CueTranscriptMatch
from .models import AlignmentUnit


@dataclass(frozen=True)
class HiddenVocalGap:
    after_cue_index: int
    text: str
    start: float
    end: float


def infer_hidden_vocal_gaps(
    matches: Sequence[CueTranscriptMatch],
    transcript_units: Sequence[AlignmentUnit],
    **_: object,
) -> list[HiddenVocalGap]:
    """Automatic hidden-vocal inference is intentionally disabled.

    Real-song A/B testing showed no timing improvement, while short lyrics,
    ad-libs, and sustained endings could be misclassified as caption-free
    humming. Manual standalone parenthetical cues remain the explicit and
    reliable escape hatch.
    """

    del matches, transcript_units
    return []
