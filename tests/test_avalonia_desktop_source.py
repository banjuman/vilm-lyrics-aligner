import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop" / "VilmLyricsAligner.Desktop"


class AvaloniaDesktopSourceTests(unittest.TestCase):
    def test_native_desktop_keeps_vilm_visual_language(self):
        xaml = (DESKTOP / "MainWindow.axaml").read_text(encoding="utf-8")
        self.assertIn('<SolidColorBrush x:Key="VilmBackground">#F2E9D2</SolidColorBrush>', xaml)
        self.assertIn('<SolidColorBrush x:Key="VilmGreen">#043D20</SolidColorBrush>', xaml)
        self.assertIn('Style Selector="Button.lang.active"', xaml)
        self.assertIn('Background="#20251F"', xaml)
        self.assertIn('Content="voiceandfilm.com"', xaml)
        self.assertIn('Content="@voiceandfilm"', xaml)
        self.assertIn('FontFamily="Segoe UI, Malgun Gothic, Apple SD Gothic Neo"', xaml)
        self.assertIn('Text="Vilm Lyrics Aligner" FontSize="15" FontWeight="Bold"', xaml)
        self.assertIn('FontFamily="Consolas, Malgun Gothic, Apple SD Gothic Neo"', xaml)
        self.assertIn('<Setter Property="FontWeight" Value="SemiBold" />', xaml)
        self.assertIn('Button.footerLink:pointerover', xaml)
        self.assertIn('Button.footerLink:pressed', xaml)

    def test_beginner_help_is_available_in_both_languages(self):
        xaml = (DESKTOP / "MainWindow.axaml").read_text(encoding="utf-8")
        source = (DESKTOP / "MainWindow.axaml.cs").read_text(encoding="utf-8")
        help_source = (DESKTOP / "HelpWindow.cs").read_text(encoding="utf-8")
        self.assertIn('x:Name="HelpButton"', xaml)
        self.assertIn('private async void Help_Click', source)
        self.assertIn('Manual (advanced)', help_source)
        self.assertIn('수동(고급) 모드', help_source)
        self.assertIn('invisible anchor cue', help_source)

    def test_processing_log_uses_a_full_width_custom_panel(self):
        xaml = (DESKTOP / "MainWindow.axaml").read_text(encoding="utf-8")
        source = (DESKTOP / "MainWindow.axaml.cs").read_text(encoding="utf-8")
        self.assertIn('x:Name="DetailsPanel" IsVisible="False"', xaml)
        self.assertIn('x:Name="CopyLogButton"', xaml)
        self.assertIn('Background="#20251F"', xaml)
        self.assertNotIn('x:Name="DetailsExpander"', xaml)
        self.assertIn('SetDetailsExpanded', source)
        self.assertIn('x:Name="MainScroll"', xaml)
        self.assertIn('x:Name="ContentBottomSpacer" Height="16"', xaml)
        self.assertNotIn('Margin="0,0,0,8" Padding="8,7,8,18"', xaml)
        self.assertIn('MainScroll.UpdateLayout()', source)
        self.assertIn('MainScroll.ScrollToEnd()', source)
        self.assertIn('DispatcherTimer.RunOnce', source)
        self.assertIn('clipboard.SetTextAsync', source)

    def test_manual_controls_show_readable_units_and_footer_spacing(self):
        xaml = (DESKTOP / "MainWindow.axaml").read_text(encoding="utf-8")
        source = (DESKTOP / "MainWindow.axaml.cs").read_text(encoding="utf-8")
        self.assertIn('x:Name="MaxCharsInput" Width="136"', xaml)
        self.assertIn('x:Name="MaxDurationInput" Width="118"', xaml)
        self.assertIn('MaxCharsInput.FormatString = _language == "ko" ? "0 자" : "0 chars";', source)
        self.assertIn('MaxDurationInput.FormatString = _language == "ko" ? "0 초" : "0 s";', source)
        self.assertIn('Classes="card last"', xaml)
        self.assertIn('MinHeight="32" Padding="8,5"', xaml)
        self.assertIn('VerticalContentAlignment="Center" Click="Help_Click"', xaml)

    def test_english_is_the_safe_default_and_korean_is_available(self):
        source = (DESKTOP / "MainWindow.axaml.cs").read_text(encoding="utf-8")
        self.assertIn('private string _language = "en";', source)
        self.assertIn('return language is "ko" ? "ko" : "en";', source)
        self.assertIn('["ko"] = new Dictionary<string, string>', source)

    def test_language_switch_updates_status_and_file_picker_labels(self):
        source = (DESKTOP / "MainWindow.axaml.cs").read_text(encoding="utf-8")
        self.assertIn('new FilePickerFileType(Tr("media_file_type"))', source)
        self.assertIn('new FilePickerFileType(Tr("text_file_type"))', source)
        self.assertIn('new FilePickerFileType(Tr("subtitle_file_type"))', source)
        self.assertIn("private void RefreshStatus()", source)
        self.assertIn("ModeBox.SelectedIndex = -1;", source)
        self.assertIn("EndHoldBox.SelectedIndex = -1;", source)
        self.assertNotIn("ModeBox.ItemsSource =", source)
        self.assertNotIn("EndHoldBox.ItemsSource =", source)
        self.assertIn("RefreshStatus();", source)
        self.assertIn('Tr("technical_details")', source)

    def test_alignment_runs_in_a_cancellable_child_process(self):
        source = (DESKTOP / "EngineBridge.cs").read_text(encoding="utf-8")
        self.assertIn("CreateNoWindow = true", source)
        self.assertIn("StandardOutputEncoding = Encoding.UTF8", source)
        self.assertIn("StandardErrorEncoding = Encoding.UTF8", source)
        self.assertIn("process.Kill(true)", source)
        self.assertIn('"--timeline-anchor"', source)
        self.assertIn('"--partial-range"', source)

    def test_installer_publishes_and_embeds_native_desktop(self):
        build = (ROOT / "installer" / "windows" / "build-installer.ps1").read_text(encoding="utf-8")
        setup = (ROOT / "installer" / "windows" / "Setup" / "Program.cs").read_text(encoding="utf-8")
        self.assertIn("dotnet publish $DesktopProject", build)
        self.assertIn('Join-Path $Stage "desktop\\VilmLyricsAligner.exe"', build)
        self.assertIn("StandardOutputEncoding = Encoding.UTF8", setup)
        self.assertIn("StandardErrorEncoding = Encoding.UTF8", setup)

    def test_macos_setup_waits_for_explicit_open_after_all_components_finish(self):
        source = (DESKTOP / "SetupWindow.cs").read_text(encoding="utf-8")
        self.assertIn("private bool _installationComplete;", source)
        self.assertIn("_installationComplete = true;", source)
        self.assertIn('Content = "Open Vilm Lyrics Aligner"', source)
        self.assertIn("Restart DaVinci Resolve before opening the Vilm panel.", source)


if __name__ == "__main__":
    unittest.main()
