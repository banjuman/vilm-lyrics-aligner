from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from lyrics_aligner.cleanup import cleanup_old_diagnostics, cleanup_stale_workdirs


class CleanupTests(unittest.TestCase):
    def test_removes_only_old_owned_temp_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old_owned = root / "lyrics-aligner-old"
            new_owned = root / "lyrics-aligner-new"
            unrelated = root / "another-tool-old"
            for path in (old_owned, new_owned, unrelated):
                path.mkdir()
            os.utime(old_owned, (10, 10))
            os.utime(unrelated, (10, 10))
            removed = cleanup_stale_workdirs(
                temp_root=root, max_age_seconds=50, now=100
            )
            self.assertEqual(removed, 1)
            self.assertFalse(old_owned.exists())
            self.assertTrue(new_owned.exists())
            self.assertTrue(unrelated.exists())

    def test_removes_only_old_json_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old_json = root / "old.json"
            new_json = root / "new.json"
            other = root / "keep.txt"
            for path in (old_json, new_json, other):
                path.write_text("x", encoding="utf-8")
            os.utime(old_json, (10, 10))
            os.utime(other, (10, 10))
            removed = cleanup_old_diagnostics(root, max_age_seconds=50, now=100)
            self.assertEqual(removed, 1)
            self.assertFalse(old_json.exists())
            self.assertTrue(new_json.exists())
            self.assertTrue(other.exists())


if __name__ == "__main__":
    unittest.main()
