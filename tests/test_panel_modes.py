from __future__ import annotations

import unittest
from pathlib import Path


class ResolvePanelModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (Path(__file__).parents[1] / "resolve" / "LyricsAligner.py").read_text(
            encoding="utf-8"
        )

    def test_exposes_exactly_auto_and_manual_modes(self) -> None:
        self.assertIn('"자동 모드"', self.source)
        self.assertIn('"수동(고급) 모드"', self.source)
        self.assertIn('"ID": "modeSelector"', self.source)
        self.assertNotIn('"ID": "autoMode"', self.source)

    def test_manual_mode_directly_reveals_manual_options(self) -> None:
        self.assertIn('"ID": "manualGroup"', self.source)
        self.assertIn('win.Find("manualGroup").Hidden = not manual', self.source)
        self.assertNotIn("advancedToggle", self.source)

    def test_device_selector_is_outside_manual_only_group(self) -> None:
        manual_start = self.source.index('ui.VGroup({"ID": "manualGroup"')
        device_position = self.source.index('ui.ComboBox({"ID": "deviceSelector"')
        range_position = self.source.index('ui.ComboBox({"ID": "rangeSelector"')
        self.assertLess(manual_start, device_position)
        self.assertLess(device_position, range_position)

    def test_auto_flag_and_manual_values_are_captured_before_worker_starts(self) -> None:
        self.assertIn('if options["automatic"]:\n        command.append("--auto-segment")', self.source)
        self.assertIn('"max_duration_ms": int(win.Find("maxDuration").Value) * 1000', self.source)
        self.assertIn('"end_pad_ms": [300, 500, 1000, 1500]', self.source)
        self.assertIn('str(500 if options["automatic"] else options["end_pad_ms"])', self.source)

    def test_obsolete_diagnostics_and_device_choice_are_not_visible(self) -> None:
        self.assertNotIn("균등 타이밍", self.source)
        self.assertNotIn('"ID": "forceCpu"', self.source)
        self.assertNotIn("ui.RadioButton", self.source)
        self.assertIn('"ID": "deviceSelector"', self.source)
        self.assertIn('[tr(accelerator_key), tr("cpu_device")]', self.source)
        self.assertIn('else [tr("cpu_device")]', self.source)
        self.assertIn('child_env["LYRICS_ALIGNER_DEVICE"] = options["device"]', self.source)
        self.assertIn('"ID": "rangeSelector"', self.source)


if __name__ == "__main__":
    unittest.main()
