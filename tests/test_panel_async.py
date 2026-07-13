from __future__ import annotations

import unittest
from pathlib import Path


class ResolvePanelExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (Path(__file__).parents[1] / "resolve" / "LyricsAligner.py").read_text(
            encoding="utf-8"
        )

    def test_alignment_runs_synchronously_on_resolve_python(self) -> None:
        self.assertIn("def run_alignment_sync(options):", self.source)
        self.assertIn("run_streaming_process(", self.source)
        self.assertNotIn("threading.Thread(", self.source)
        self.assertNotIn("QueueEvent(win", self.source)
        self.assertNotIn('"ID": "cancel"', self.source)

    def test_inout_uses_partial_lyric_alignment(self) -> None:
        self.assertIn("if use_marks and not selected_range.used_marks:", self.source)
        self.assertIn('command.append("--partial-range")', self.source)
        self.assertIn('"partial_range": selected_range.used_marks', self.source)
        self.assertIn('"--offset-seconds"', self.source)
        self.assertIn('selected_range.start_frame - int(timeline.GetStartFrame())', self.source)

    def test_existing_subtitles_are_preserved(self) -> None:
        self.assertIn('timeline.GetTrackCount("subtitle") > 0', self.source)
        self.assertIn('win.Find("log").Append(tr("existing_subtitles"))', self.source)


if __name__ == "__main__":
    unittest.main()
