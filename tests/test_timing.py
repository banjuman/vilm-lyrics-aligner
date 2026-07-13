


import unittest

from lyrics_aligner.models import Cue
from lyrics_aligner.timing import VocalActivity, polish_singing_cue_times


class SingingTimingTests(unittest.TestCase):
    def test_snaps_start_and_extends_to_vocal_tail_plus_hold(self):
        activity = VocalActivity.from_segments(10, [(0.95, 3.4), (5.0, 6.0)])
        cues = [Cue("first", 1.1, 3.0), Cue("second", 5.1, 5.8)]
        polished = polish_singing_cue_times(cues, activity=activity)
        self.assertAlmostEqual(polished[0].start, 1.1, places=2)
        self.assertAlmostEqual(polished[0].end, 3.9, places=1)

    def test_activity_cannot_pull_a_guarded_lyric_start_back_to_a_hum(self):
        activity = VocalActivity.from_segments(10, [(0.8, 1.0), (1.2, 3.0)])
        cue = Cue("lyric", 1.1, 2.5)
        polished = polish_singing_cue_times([cue], activity=activity)
        self.assertGreaterEqual(polished[0].start, 1.1)

    def test_long_bad_alignment_is_capped_after_first_phrase(self):
        activity = VocalActivity.from_segments(
            40, [(1.0, 8.0), (30.0, 34.0)]
        )
        cues = [Cue("before interlude", 1.0, 30.0), Cue("after", 30.0, 34.0)]
        polished = polish_singing_cue_times(
            cues, activity=activity, max_duration_ms=10000
        )
        self.assertAlmostEqual(polished[0].end, 8.5, places=1)
        self.assertLessEqual(polished[0].end - polished[0].start, 10.0)

    def test_soft_cap_does_not_cut_a_long_active_vocal(self):
        activity = VocalActivity.from_segments(20, [(1.0, 13.0)])
        cues = [Cue("long melisma", 1.0, 13.0)]
        polished = polish_singing_cue_times(
            cues, activity=activity, max_duration_ms=10000
        )
        self.assertGreaterEqual(polished[0].end, 13.0)


if __name__ == "__main__":
    unittest.main()
