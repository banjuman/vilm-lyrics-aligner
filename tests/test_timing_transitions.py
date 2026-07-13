import unittest

from lyrics_aligner.models import Cue
from lyrics_aligner.timing import VocalActivity, polish_singing_cue_times


class SingingTransitionTests(unittest.TestCase):
    def test_touching_lines_protect_previous_end_without_delaying_next(self):
        activity = VocalActivity.from_segments(10, [(1.0, 3.0), (2.9, 5.0)])
        cues = [Cue("first", 1.0, 3.0), Cue("second", 3.02, 5.0)]
        polished = polish_singing_cue_times(cues, activity=activity)
        self.assertGreaterEqual(polished[0].end, 3.0)
        self.assertGreaterEqual(polished[1].start, polished[0].end)
        self.assertLessEqual(polished[1].start, 3.02)

    def test_continuing_activity_is_not_treated_as_a_new_onset(self):
        activity = VocalActivity.from_segments(10, [(1.0, 5.0)])
        self.assertAlmostEqual(activity.snap_start(3.0), 3.0)


if __name__ == "__main__":
    unittest.main()
