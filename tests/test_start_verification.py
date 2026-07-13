from __future__ import annotations

import unittest

from lyrics_aligner.matching import CueTranscriptMatch
from lyrics_aligner.models import Cue
from lyrics_aligner.start_verification import refine_start_from_evidence


def match(
    index: int,
    start: float | None,
    end: float | None,
    *,
    similarity: float = 1.0,
    coverage: float = 1.0,
    exact: int = 5,
) -> CueTranscriptMatch:
    return CueTranscriptMatch(
        cue_index=index,
        source_text=f"line {index}",
        transcript_text=f"heard {index}",
        start=start,
        end=end,
        similarity=similarity,
        coverage=coverage,
        exact_characters=exact,
        status="match" if similarity >= 0.84 else "weak",
    )


class StartEvidenceTests(unittest.TestCase):
    def test_later_global_start_trims_a_swallowed_sustain(self) -> None:
        previous = match(0, 1.0, 3.0)
        current = match(1, 3.0, 6.0)
        local = Cue("next lyric", 3.05, 6.05)
        global_cue = Cue("next lyric", 4.0, 6.10)

        refined, decisions = refine_start_from_evidence(
            1,
            local,
            current,
            previous_match=previous,
            local_cue=local,
            global_cue=global_cue,
        )

        self.assertAlmostEqual(refined.start, 4.0)
        self.assertEqual(decisions[-1].kind, "sustained_boundary_consensus")

    def test_dense_rap_boundary_is_unchanged_when_alignments_agree(self) -> None:
        previous = match(0, 1.0, 3.0)
        current = match(1, 3.0, 5.0)
        local = Cue("fast next lyric", 3.02, 5.0)
        global_cue = Cue("fast next lyric", 3.16, 5.05)

        refined, decisions = refine_start_from_evidence(
            1,
            local,
            current,
            previous_match=previous,
            local_cue=local,
            global_cue=global_cue,
        )

        self.assertAlmostEqual(refined.start, local.start)
        self.assertFalse(
            any(item.kind == "sustained_boundary_consensus" for item in decisions)
        )

    def test_whole_phrase_drift_is_not_mistaken_for_a_sustain(self) -> None:
        previous = match(0, 1.0, 3.0)
        current = match(1, 3.1, 6.0)
        local = Cue("next lyric", 3.1, 6.0)
        global_cue = Cue("next lyric", 4.0, 7.0)

        refined, decisions = refine_start_from_evidence(
            1,
            local,
            current,
            previous_match=previous,
            local_cue=local,
            global_cue=global_cue,
        )

        self.assertAlmostEqual(refined.start, local.start)
        self.assertFalse(
            any(item.kind == "sustained_boundary_consensus" for item in decisions)
        )

    def test_separate_phrases_do_not_use_transition_rule(self) -> None:
        previous = match(0, 1.0, 3.0)
        current = match(1, 4.5, 7.0)
        local = Cue("next lyric", 4.5, 7.0)
        global_cue = Cue("next lyric", 5.4, 7.1)

        refined, decisions = refine_start_from_evidence(
            1,
            local,
            current,
            previous_match=previous,
            local_cue=local,
            global_cue=global_cue,
        )

        self.assertAlmostEqual(refined.start, local.start)
        self.assertFalse(
            any(item.kind == "sustained_boundary_consensus" for item in decisions)
        )

    def test_weak_asr_cannot_trigger_consensus_correction(self) -> None:
        previous = match(0, 1.0, 3.0)
        current = match(1, 3.0, 6.0, similarity=0.25, coverage=0.3, exact=1)
        local = Cue("next lyric", 3.0, 6.0)
        global_cue = Cue("next lyric", 4.0, 6.1)

        refined, decisions = refine_start_from_evidence(
            1,
            local,
            current,
            previous_match=previous,
            local_cue=local,
            global_cue=global_cue,
        )

        self.assertAlmostEqual(refined.start, local.start)
        self.assertEqual(decisions, [])


if __name__ == "__main__":
    unittest.main()
