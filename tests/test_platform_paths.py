import os
import unittest
from pathlib import Path
from unittest.mock import patch

from lyrics_aligner.platform_paths import application_data_root


class PlatformPathTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch("lyrics_aligner.platform_paths.sys.platform", "darwin")
    @patch("lyrics_aligner.platform_paths.Path.home", return_value=Path("/Users/tester"))
    def test_macos_uses_application_support(self, _home):
        self.assertEqual(
            application_data_root(),
            Path("/Users/tester/Library/Application Support/Vilm Lyrics Aligner"),
        )

    @patch.dict(os.environ, {"LYRICS_ALIGNER_APP_ROOT": "/private/test-root"}, clear=True)
    def test_explicit_root_wins_on_every_platform(self):
        self.assertEqual(application_data_root(), Path("/private/test-root"))


if __name__ == "__main__":
    unittest.main()
