from __future__ import annotations

import unittest

from lyrics_aligner.lyric_annotations import split_manual_lyrics_with_hidden


class ManualLyricAnnotationTests(unittest.TestCase):
    def test_standalone_parenthetical_line_becomes_hidden_cue(self) -> None:
        texts, hidden = split_manual_lyrics_with_hidden(
            "보이는 가사\n(흐음)\n다음 가사", 30
        )
        self.assertEqual(texts, ["보이는 가사", "흐음", "다음 가사"])
        self.assertEqual(hidden, {1})

    def test_parentheses_inside_visible_lyric_remain_visible(self) -> None:
        texts, hidden = split_manual_lyrics_with_hidden(
            "사랑해 (정말) 오늘도", 30
        )
        self.assertEqual(texts, ["사랑해 (정말) 오늘도"])
        self.assertEqual(hidden, set())

    def test_empty_parentheses_are_not_a_hidden_alignment_cue(self) -> None:
        texts, hidden = split_manual_lyrics_with_hidden("()\n다음", 30)
        self.assertEqual(texts, ["()", "다음"])
        self.assertEqual(hidden, set())


if __name__ == "__main__":
    unittest.main()
