import unittest

from lyrics_aligner.models import Cue
from lyrics_aligner.srt import format_timestamp, render_srt


class SrtTests(unittest.TestCase):
    def test_formats_with_millisecond_rounding(self):
        self.assertEqual(format_timestamp(3661.2346), "01:01:01,235")

    def test_offsets_partial_range_timecodes(self):
        rendered = render_srt([Cue("구간", 0.5, 1.5)], offset_seconds=80.5)
        self.assertIn("00:01:21,000 --> 00:01:22,000", rendered)

    def test_timeline_anchor_preserves_zero_origin_for_nle_import(self):
        rendered = render_srt(
            [Cue("첫 가사", 12.0, 13.0)],
            timeline_anchor=True,
        )
        self.assertIn("1\n00:00:00,000 --> 00:00:00,500\n\u2800", rendered)
        self.assertIn("2\n00:00:12,000 --> 00:00:13,000\n첫 가사", rendered)

    def test_timeline_anchor_is_not_duplicated_at_zero(self):
        rendered = render_srt(
            [Cue("바로 시작", 0.0, 1.0)],
            timeline_anchor=True,
        )
        self.assertNotIn("\u2800", rendered)
        self.assertTrue(rendered.startswith("1\n00:00:00,000"))

    def test_renders_subrip_blocks(self):
        rendered = render_srt([Cue("안녕", 0.1, 1.2), Cue("hello", 1.5, 2.0)])
        self.assertIn("1\n00:00:00,100 --> 00:00:01,200\n안녕", rendered)
        self.assertTrue(rendered.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
