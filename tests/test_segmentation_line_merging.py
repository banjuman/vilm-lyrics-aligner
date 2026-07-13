from __future__ import annotations

import unittest

from lyrics_aligner.models import Cue
from lyrics_aligner.segmentation import merge_obvious_wrapped_lines


class ConservativeLineMergeTests(unittest.TestCase):
    def test_merges_only_obvious_continuous_display_wrap(self) -> None:
        texts = ["가" * 20, "나" * 8]
        merged, count = merge_obvious_wrapped_lines(
            texts,
            {
                0: [Cue(texts[0], 1.0, 3.0)],
                1: [Cue(texts[1], 3.08, 4.2)],
            },
            preferred_chars=30,
        )

        self.assertEqual(count, 1)
        self.assertEqual(merged[0][0].text, f"{texts[0]} {texts[1]}")
        self.assertEqual(merged[1], [])

    def test_keeps_short_intentional_lyric_lines_separate(self) -> None:
        texts = ["내 곁에", "있어주세요"]
        merged, count = merge_obvious_wrapped_lines(
            texts,
            {
                0: [Cue(texts[0], 1.0, 2.0)],
                1: [Cue(texts[1], 2.05, 3.2)],
            },
            preferred_chars=30,
        )

        self.assertEqual(count, 0)
        self.assertEqual(merged[0][0].text, texts[0])
        self.assertEqual(merged[1][0].text, texts[1])

    def test_never_merges_across_a_blank_paragraph(self) -> None:
        texts = ["가" * 20, "나" * 8]
        merged, count = merge_obvious_wrapped_lines(
            texts,
            {
                0: [Cue(texts[0], 1.0, 3.0)],
                1: [Cue(texts[1], 3.08, 4.2)],
            },
            preferred_chars=30,
            paragraph_barriers={1},
        )

        self.assertEqual(count, 0)
        self.assertEqual(merged[0][0].text, texts[0])
        self.assertEqual(merged[1][0].text, texts[1])


if __name__ == "__main__":
    unittest.main()
