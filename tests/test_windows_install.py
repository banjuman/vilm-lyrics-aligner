import unittest
from pathlib import Path

from lyrics_aligner.windows_install import _uninstall_script


class WindowsUninstallTests(unittest.TestCase):
    def test_script_requires_expected_app_folder_and_resolve_shutdown(self):
        script = _uninstall_script(
            Path(r"C:\Users\Test\AppData\Local\LyricsAligner"),
            Path(r"C:\ProgramData\Plugin\Vilm Lyrics Aligner.py"),
            Path(r"C:\ProgramData\LyricsAligner"),
        )
        self.assertIn("Get-Process -Name Resolve", script)
        self.assertIn("Vilm Lyrics Aligner.py", script)
        self.assertIn("LyricsAligner.py", script)
        self.assertIn("GetFileName($AppRoot) -ne 'LyricsAligner'", script)
        self.assertIn("Remove-Item -LiteralPath $AppRoot -Recurse", script)
        self.assertIn("Vilm Lyrics Aligner.py", script)


if __name__ == "__main__":
    unittest.main()
