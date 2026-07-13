

import unittest

from lyrics_aligner.matching import CueTranscriptMatch
from lyrics_aligner.models import Cue
from lyrics_aligner.pipeline import _guard_lexical_start, _select_window_matches


def match(index, *, start, similarity, coverage, exact=2, status="weak"):
    return CueTranscriptMatch(
        cue_index=index,
        source_text=f"line {index}",
        transcript_text="heard",
        start=start,
        end=None if start is None else start + 1.0,
        similarity=similarity,
        coverage=coverage,
        exact_characters=exact,
        status=status,
    )


class HybridAnchorPolicyTests(unittest.TestCase):
    def test_weak_asr_is_not_used_as_a_local_start_anchor(self):
        matches = [
            match(0, start=232.4, similarity=0.50, coverage=0.375),
            match(1, start=234.7, similarity=0.53, coverage=0.45, exact=5),
        ]
        global_cues = [Cue("first", 238.0, 246.8), Cue("second", 247.3, 278.0)]
        selected = _select_window_matches(matches, global_cues)
        self.assertEqual(selected, [])

    def test_strong_anchor_is_kept_even_when_global_alignment_drifted(self):
        matches = [match(0, start=10.0, similarity=0.9, coverage=0.9, exact=5)]
        selected = _select_window_matches(matches, [Cue("line", 30.0, 32.0)])
        self.assertEqual(selected, matches)

    def test_lexical_floor_prevents_humming_from_opening_next_lyric(self):
        source = Cue("next lyric", 10.0, 14.0)
        observed = match(0, start=12.0, similarity=0.8, coverage=0.8, exact=4)
        guarded = _guard_lexical_start(source, observed)
        self.assertAlmostEqual(guarded.start, 11.95)
        self.assertEqual(guarded.end, 14.0)


if __name__ == "__main__":
    unittest.main()
