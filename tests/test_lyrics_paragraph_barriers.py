from __future__ import annotations

import unittest

from lyrics_aligner.lyrics import split_lyrics_with_paragraph_barriers


class ParagraphBarrierTests(unittest.TestCase):
    def test_blank_stanza_records_a_non_merge_boundary(self) -> None:
        cues, barriers = split_lyrics_with_paragraph_barriers(
            "첫 줄\n둘째 줄\n\n새 절\n마지막 줄", max_chars=30
        )
        self.assertEqual(cues, ["첫 줄", "둘째 줄", "새 절", "마지막 줄"])
        self.assertEqual(barriers, {2})


if __name__ == "__main__":
    unittest.main()
