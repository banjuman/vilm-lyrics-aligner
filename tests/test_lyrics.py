import unittest

from lyrics_aligner.lyrics import map_units_to_cues, polish_cue_times, split_lyrics
from lyrics_aligner.models import AlignmentUnit, Cue


class SplitLyricsTests(unittest.TestCase):
    def test_preserves_short_lines_and_blank_stanzas(self):
        self.assertEqual(split_lyrics("짧아\n\n한 단어\n", 30), ["짧아", "한 단어"])

    def test_splits_long_line_near_space(self):
        result = split_lyrics("this is a moderately long English lyric line", 20)
        self.assertTrue(all(len(part) <= 20 for part in result))
        self.assertEqual(" ".join(result), "this is a moderately long English lyric line")

    def test_hard_splits_korean_without_spaces(self):
        result = split_lyrics("가" * 31, 30)
        self.assertEqual([len(part) for part in result], [30, 1])


class MappingTests(unittest.TestCase):
    def test_maps_mixed_korean_english_units_to_lines(self):
        lines = ["안녕 hello", "다시 만나"]
        units = [
            AlignmentUnit("안", 0.1, 0.2),
            AlignmentUnit("녕", 0.2, 0.4),
            AlignmentUnit("hello", 0.5, 1.0),
            AlignmentUnit("다", 1.2, 1.3),
            AlignmentUnit("시", 1.3, 1.5),
            AlignmentUnit("만", 1.6, 1.8),
            AlignmentUnit("나", 1.8, 2.1),
        ]
        cues = map_units_to_cues(lines, units)
        self.assertEqual(cues[0], Cue("안녕 hello", 0.1, 1.0))
        self.assertEqual(cues[1], Cue("다시 만나", 1.2, 2.1))

    def test_reports_transcript_mismatch(self):
        with self.assertRaisesRegex(ValueError, "performed lyrics may differ"):
            map_units_to_cues(["정답 가사"], [AlignmentUnit("완전다름", 0, 1)])

    def test_polishing_does_not_overlap_next_cue(self):
        cues = [Cue("하나", 1.0, 1.8), Cue("둘", 2.0, 2.4)]
        result = polish_cue_times(cues, lead_ms=100, end_pad_ms=500, min_gap_ms=20)
        self.assertAlmostEqual(result[0].start, 0.9)
        self.assertAlmostEqual(result[0].end, 1.88)
        self.assertAlmostEqual(result[1].start, 1.9)


if __name__ == "__main__":
    unittest.main()
