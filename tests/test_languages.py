from __future__ import annotations

import unittest

from lyrics_aligner.languages import WHISPER_LANGUAGES, whisper_language_code


class LanguageTests(unittest.TestCase):
    def test_auto_is_passed_to_whisper_as_no_language_hint(self) -> None:
        self.assertIsNone(whisper_language_code("auto"))
        self.assertIsNone(whisper_language_code(None))

    def test_names_and_codes_are_normalized(self) -> None:
        self.assertEqual(whisper_language_code("Korean"), "ko")
        self.assertEqual(whisper_language_code("EN"), "en")

    def test_full_multilingual_catalog_is_available(self) -> None:
        self.assertGreaterEqual(len(WHISPER_LANGUAGES), 100)
        self.assertIn(("yue", "Cantonese"), WHISPER_LANGUAGES)


if __name__ == "__main__":
    unittest.main()
