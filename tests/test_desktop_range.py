import unittest
from pathlib import Path

from lyrics_aligner.cli import build_parser


class DesktopRangeTests(unittest.TestCase):
    def test_cli_accepts_media_range(self):
        args = build_parser().parse_args(
            [
                "align", "media.mov", "lyrics.txt", "-o", "out.srt",
                "--range-start", "12.5", "--range-end", "42.25",
            ]
        )
        self.assertEqual(args.range_start, 12.5)
        self.assertEqual(args.range_end, 42.25)

    def test_pipeline_offsets_selected_range_to_original_media(self):
        source = (Path(__file__).resolve().parents[1] / "lyrics_aligner" / "pipeline.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("offset_seconds=offset_seconds + range_start", source)
        self.assertIn("partial_range = True", source)

    def test_desktop_is_registered_as_gui_entrypoint(self):
        project = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('[project.gui-scripts]', project)
        self.assertIn('vilm-lyrics-aligner = "lyrics_aligner.desktop:main"', project)


if __name__ == "__main__":
    unittest.main()
