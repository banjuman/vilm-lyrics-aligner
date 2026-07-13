from __future__ import annotations

import unittest

from lyrics_aligner.hidden_vocals import infer_hidden_vocal_gaps
from lyrics_aligner.models import AlignmentUnit


class AutomaticHiddenVocalRollbackTests(unittest.TestCase):
    def test_transcribed_humming_never_changes_automatic_timing(self) -> None:
        result = infer_hidden_vocal_gaps(
            [], [AlignmentUnit("음", 2.0, 3.0)]
        )
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
