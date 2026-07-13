from __future__ import annotations

import unittest

from lyrics_aligner.models import Cue
from lyrics_aligner.pipeline import _preserve_source_order


class SourceOrderPolicyTests(unittest.TestCase):
    def test_rejects_later_source_line_that_jumps_back_in_time(self) -> None:
        cues, rejected = _preserve_source_order(
            [
                (27, Cue("의리라도", 237.5, 240.7)),
                (27, Cue("괜찮은데", 244.3, 247.1)),
                (28, Cue("조금 미지근해도 괜찮은데", 247.3, 250.4)),
                (29, Cue("나 정말 그대 필요한데", 241.2, 246.3)),
            ]
        )

        self.assertEqual(
            [cue.text for cue in cues],
            ["의리라도", "괜찮은데", "조금 미지근해도 괜찮은데"],
        )
        self.assertEqual(rejected, [29])

    def test_allows_close_overlapping_lines_without_reordering(self) -> None:
        cues, rejected = _preserve_source_order(
            [
                (0, Cue("앞 소절", 10.0, 14.0)),
                (1, Cue("다음 소절", 9.85, 13.0)),
            ]
        )
        self.assertEqual([cue.text for cue in cues], ["앞 소절", "다음 소절"])
        self.assertEqual(rejected, [])


if __name__ == "__main__":
    unittest.main()
