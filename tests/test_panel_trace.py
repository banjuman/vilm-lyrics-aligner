from __future__ import annotations

import unittest
from pathlib import Path


class PanelTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (Path(__file__).parents[1] / "resolve" / "LyricsAligner.py").read_text(
            encoding="utf-8"
        )

    def test_trace_captures_range_render_and_engine_boundaries(self) -> None:
        for marker in (
            "run requested",
            "range: use_marks=",
            "render complete:",
            "synchronous alignment entered",
            "starting engine synchronously:",
            "engine returned:",
            "job completed",
        ):
            self.assertIn(marker, self.source)

    def test_trace_does_not_record_lyrics_text(self) -> None:
        trace_calls = [line for line in self.source.splitlines() if "trace(" in line]
        self.assertFalse(any('options["lyrics"]' in line for line in trace_calls))


if __name__ == "__main__":
    unittest.main()
