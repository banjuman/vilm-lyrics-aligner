from __future__ import annotations

import unittest

from lyrics_aligner.models import Cue
from lyrics_aligner.pipeline import _is_hidden, _mark_hidden
from lyrics_aligner.timing import VocalActivity, polish_singing_cue_times


class HiddenCueTimingTests(unittest.TestCase):
    def test_hidden_vocal_reserves_time_then_disappears_from_output(self) -> None:
        activity = VocalActivity.from_segments(
            8.0, [(1.0, 2.0), (2.4, 3.2), (4.0, 5.0)]
        )
        timed = polish_singing_cue_times(
            [
                Cue("앞 가사", 1.0, 2.0),
                Cue(_mark_hidden("흐음"), 2.4, 3.2),
                Cue("다음 가사", 4.0, 5.0),
            ],
            activity=activity,
            end_hold_ms=500,
            min_gap_ms=80,
        )
        visible = [cue for cue in timed if not _is_hidden(cue)]

        self.assertEqual([cue.text for cue in visible], ["앞 가사", "다음 가사"])
        self.assertLessEqual(visible[0].end, 2.4)
        self.assertGreaterEqual(visible[1].start, 4.0)


if __name__ == "__main__":
    unittest.main()
