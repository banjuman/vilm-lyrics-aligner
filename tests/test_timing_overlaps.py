import unittest

from lyrics_aligner.models import Cue
from lyrics_aligner.timing import polish_singing_cue_times


class OverlapPolicyTests(unittest.TestCase):
    def test_conflicting_raw_end_switches_directly_at_next_cue(self):
        cues = [Cue("first", 1.0, 8.0), Cue("second", 5.0, 7.0)]
        polished = polish_singing_cue_times(cues, activity=None, lead_ms=0)
        self.assertAlmostEqual(polished[0].end, 5.0, places=2)
        self.assertAlmostEqual(polished[1].start, 5.0, places=2)
        self.assertGreater(polished[1].end - polished[1].start, 1.0)


if __name__ == "__main__":
    unittest.main()
