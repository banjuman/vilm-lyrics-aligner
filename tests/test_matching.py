import unittest

from lyrics_aligner.matching import compare_lyrics_to_transcript
from lyrics_aligner.models import AlignmentUnit


class TranscriptMatchingTests(unittest.TestCase):
    def test_matches_mixed_language_lines_monotonically(self):
        cues = ["내 곁에 stay", "오늘도 좋아"]
        units = [
            AlignmentUnit("내", 1.0, 1.2),
            AlignmentUnit("곁에", 1.2, 1.6),
            AlignmentUnit("stay", 1.6, 2.0),
            AlignmentUnit("오늘도", 3.0, 3.5),
            AlignmentUnit("좋아", 3.5, 4.0),
        ]
        matches = compare_lyrics_to_transcript(cues, units)
        self.assertEqual([item.status for item in matches], ["match", "match"])
        self.assertAlmostEqual(matches[1].start, 3.0)

    def test_reports_changed_text_but_keeps_source(self):
        cues = ["너를 사랑해"]
        units = [
            AlignmentUnit("정말", 1.0, 1.5),
            AlignmentUnit("사랑해", 1.5, 2.5),
        ]
        match = compare_lyrics_to_transcript(cues, units)[0]
        self.assertEqual(match.source_text, "너를 사랑해")
        self.assertEqual(match.transcript_text, "정말 사랑해")
        self.assertEqual(match.status, "changed")
        self.assertTrue(match.usable_anchor)

    def test_extra_adlib_does_not_shift_following_line(self):
        cues = ["첫 줄", "다음 줄"]
        units = [
            AlignmentUnit("첫 줄", 1.0, 2.0),
            AlignmentUnit("우우", 2.1, 2.5),
            AlignmentUnit("다음 줄", 4.0, 5.0),
        ]
        matches = compare_lyrics_to_transcript(cues, units)
        self.assertAlmostEqual(matches[1].start, 4.0)
        self.assertEqual(matches[1].status, "match")


if __name__ == "__main__":
    unittest.main()
