import unittest

from lyrics_aligner.models import Cue
from lyrics_aligner.timing import polish_singing_cue_times


class VisualTransitionGapTests(unittest.TestCase):
    def test_inserts_small_gap_when_acoustic_room_exists(self):
        cues = [Cue("first", 1.0, 2.0), Cue("second", 2.5, 3.0)]
        result = polish_singing_cue_times(
            cues, activity=None, lead_ms=0, end_hold_ms=1200, min_gap_ms=80
        )
        self.assertAlmostEqual(result[0].end, 2.42)
        self.assertAlmostEqual(result[1].start, 2.5)

    def test_drops_visual_gap_when_lines_really_touch(self):
        cues = [Cue("first", 1.0, 2.0), Cue("second", 2.02, 3.0)]
        result = polish_singing_cue_times(
            cues, activity=None, lead_ms=100, end_hold_ms=1200, min_gap_ms=80
        )
        self.assertAlmostEqual(result[0].end, 2.0)
        self.assertAlmostEqual(result[1].start, 2.0)


if __name__ == "__main__":
    unittest.main()
