import unittest
from pathlib import Path


class ResolveComboBoxApiTests(unittest.TestCase):
    def test_device_selection_does_not_depend_on_count_api(self):
        source = (Path(__file__).resolve().parents[1] / "resolve" / "LyricsAligner.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(".Count", source)
        self.assertIn('CurrentIndex == 1 else installed_backend', source)


if __name__ == "__main__":
    unittest.main()
