import unittest
from pathlib import Path


class DesktopSourceTests(unittest.TestCase):
    def test_desktop_srt_includes_nle_timeline_anchor(self):
        self.assertIn('"--timeline-anchor"', self.source)

    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / "lyrics_aligner" / "desktop.py").read_text(
            encoding="utf-8"
        )

    def test_worker_receives_ui_values_captured_on_main_thread(self):
        self.assertIn('"automatic": self.mode_box.current() == 0', self.source)
        self.assertIn('args=(lyrics_path, Path(output), selected, options)', self.source)
        worker = self.source.split("def _alignment_worker", 1)[1]
        self.assertNotIn("self.mode_box.current()", worker)
        self.assertNotIn("self.max_chars.get()", worker)

    def test_window_is_compact(self):
        self.assertIn('root.geometry("860x720")', self.source)


if __name__ == "__main__":
    unittest.main()
