from __future__ import annotations

import unittest
from pathlib import Path


class ResolvePanelInternationalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (Path(__file__).parents[1] / "resolve" / "LyricsAligner.py").read_text(
            encoding="utf-8"
        )

    def test_new_users_default_to_english(self) -> None:
        self.assertIn('DEFAULT_UI_LANGUAGE = "en"', self.source)
        self.assertIn('{"ui_language": DEFAULT_UI_LANGUAGE}', self.source)

    def test_ui_language_control_does_not_expose_audio_language(self) -> None:
        self.assertIn('"ID": "uiLanguage"', self.source)
        self.assertNotIn('"ID": "speechLanguage"', self.source)
        self.assertNotIn('"--language"', self.source)

    def test_korean_and_english_ui_text_are_equally_present(self) -> None:
        self.assertIn('"auto_mode": "자동 모드"', self.source)
        self.assertIn('"auto_mode": "Auto mode"', self.source)
        self.assertIn('"help": "사용법"', self.source)
        self.assertIn('"help": "Help"', self.source)
        self.assertIn('"output_file": "SRT 파일"', self.source)
        self.assertIn('"output_file": "SRT file"', self.source)
        self.assertIn('"cuda_device": "CUDA · NVIDIA (권장)"', self.source)
        self.assertIn('"cuda_device": "CUDA · NVIDIA (recommended)"', self.source)
        self.assertIn('"cpu_device": "CPU"', self.source)

    def test_contextual_help_stays_compact_until_requested(self) -> None:
        self.assertIn('"ID": "helpButton"', self.source)
        self.assertIn('"ID": "helpGroup", "Hidden": True', self.source)
        self.assertIn('"ID": "modeDescription"', self.source)
        self.assertIn('"ID": "rangeHint"', self.source)
        self.assertIn('win.Find("helpGroup").Hidden = not help_open', self.source)

    def test_completion_is_user_facing_and_path_stays_in_log(self) -> None:
        self.assertIn('set_status("complete")', self.source)
        self.assertIn("win.Find(\"log\").Append(f\"{tr('output_file')}", self.source)
        self.assertNotIn('"complete": "Complete: {path}"', self.source)

    def test_language_switch_preserves_and_retranslates_current_status(self) -> None:
        self.assertIn('current_status_key = "idle"', self.source)
        self.assertIn('tr(current_status_key, **current_status_values)', self.source)
        self.assertIn('FReqB_Filter": tr("text_filter")', self.source)
        self.assertIn('TEXT[ui_language]["config_missing"]', self.source)
        self.assertNotIn("설정 파일이 없습니다: {CONFIG_PATH}", self.source)

    def test_unreliable_review_markers_are_not_added(self) -> None:
        self.assertNotIn("bridge.add_review_markers", self.source)
        self.assertNotIn("complete_markers", self.source)


if __name__ == "__main__":
    unittest.main()
