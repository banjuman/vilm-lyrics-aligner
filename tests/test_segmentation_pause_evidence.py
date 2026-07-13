
from __future__ import annotations

import unittest

from lyrics_aligner.models import AlignmentUnit, Cue
from lyrics_aligner.segmentation import auto_segment_source_cues


class PauseEvidenceTests(unittest.TestCase):
    def test_global_pause_wins_when_local_window_compresses_it(self) -> None:
        result = auto_segment_source_cues(
            ["의리라도 괜찮은데"],
            {0: Cue("의리라도 괜찮은데", 234.12, 239.44)},
            [
                AlignmentUnit(" 의리라도", 237.54, 237.92),
                AlignmentUnit(" 괜찮은데", 244.30, 246.80),
            ],
            local_units_by_index={
                0: [
                    AlignmentUnit(" 의리라도", 234.12, 235.44),
                    AlignmentUnit(" 괜찮은데", 235.44, 239.44),
                ]
            },
            global_pause_indices={0},
        )

        self.assertEqual([cue.text for cue in result[0]], ["의리라도", "괜찮은데"])
        self.assertAlmostEqual(result[0][0].start, 237.54)
        self.assertAlmostEqual(result[0][1].start, 244.30)


if __name__ == "__main__":
    unittest.main()
