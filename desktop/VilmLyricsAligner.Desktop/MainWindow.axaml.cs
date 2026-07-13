using System.Diagnostics;
using System.Text.Json;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Input.Platform;
using Avalonia.Platform.Storage;
using Avalonia.Threading;

namespace VilmLyricsAligner.Desktop;

public sealed partial class MainWindow : Window
{
    private readonly EngineRuntime _runtime;
    private readonly EngineBridge _engine;
    private readonly string _preferencesPath;
    private string _language = "en";
    private string? _mediaPath;
    private CancellationTokenSource? _jobCancellation;
    private string _statusKey = "ready";
    private string? _statusDetail;


    private static readonly IReadOnlyDictionary<string, IReadOnlyDictionary<string, string>> Text =
        new Dictionary<string, IReadOnlyDictionary<string, string>>
        {
            ["en"] = new Dictionary<string, string>
            {
                ["subtitle"] = "Original lyrics to precisely timed subtitles",
                ["support"] = "Support:",
                ["help"] = "Help",
                ["media"] = "Media",
                ["media_description"] = "Choose the video or audio that matches your edit.",
                ["no_media"] = "No media selected",
                ["choose_media"] = "Choose media",
                ["full"] = "Full file",
                ["selection"] = "Selected range",
                ["range_hint"] = "Drag over the waveform to process only part of a long file.",
                ["lyrics"] = "Original lyrics",
                ["lyrics_description"] = "Paste the complete lyrics. Your text always remains the subtitle source.",
                ["load"] = "Load TXT",
                ["mode"] = "Mode",
                ["auto"] = "Auto mode (recommended)",
                ["manual"] = "Manual (advanced)",
                ["device"] = "Processing device",
                ["gpu"] = "NVIDIA GPU · CUDA",
                ["metal"] = "Apple GPU · Metal",
                ["cpu"] = "CPU",
                ["max_chars"] = "Max chars",
                ["max_seconds"] = "Max display",
                ["end_hold"] = "End hold",
                ["details"] = "Details",
                ["log_placeholder"] = "Processing messages will appear here.",
                ["log_hint"] = "Open this panel only when you need progress details or support information.",
                ["copy_log"] = "Copy log",
                ["log_copied"] = "Processing log copied.",
                ["ready"] = "Ready",
                ["reading"] = "Reading media and drawing the waveform…",
                ["processing"] = "Separating vocals and aligning the lyrics…",
                ["cancel"] = "Cancel",
                ["generate"] = "Generate SRT",
                ["need_media"] = "Choose a media file first.",
                ["need_lyrics"] = "Paste the original lyrics first.",
                ["bad_range"] = "Select at least one second of the waveform.",
                ["done"] = "SRT created successfully.",
                ["cancelled"] = "Cancelled.",
                ["failed"] = "The subtitle job failed.",
                ["save"] = "Save subtitle file",
                ["media_file_type"] = "Video and audio",
                ["text_file_type"] = "Text files",
                ["subtitle_file_type"] = "SubRip subtitles",
                ["technical_details"] = "Technical details are available in Details.",
            },
            ["ko"] = new Dictionary<string, string>
            {
                ["subtitle"] = "원문 가사를 노래에 맞춰 정밀한 자막으로 만들어요",
                ["support"] = "Support:",
                ["help"] = "도움말",
                ["media"] = "미디어",
                ["media_description"] = "실제 편집본과 타이밍이 같은 영상 또는 음원을 선택하세요.",
                ["no_media"] = "선택한 미디어가 없어요",
                ["choose_media"] = "미디어 선택",
                ["full"] = "전체 파일",
                ["selection"] = "선택 구간",
                ["range_hint"] = "긴 파일은 파형을 드래그해 필요한 부분만 처리할 수 있어요.",
                ["lyrics"] = "원문 가사",
                ["lyrics_description"] = "전체 가사를 붙여 넣으세요. 출력 문구는 항상 원문을 따라요.",
                ["load"] = "TXT 불러오기",
                ["mode"] = "모드",
                ["auto"] = "자동 모드 (권장)",
                ["manual"] = "수동(고급) 모드",
                ["device"] = "처리 장치",
                ["gpu"] = "NVIDIA GPU · CUDA",
                ["metal"] = "Apple GPU · Metal",
                ["cpu"] = "CPU",
                ["max_chars"] = "최대 글자 수",
                ["max_seconds"] = "최대 표시",
                ["end_hold"] = "끝 여운",
                ["details"] = "상세 정보",
                ["log_placeholder"] = "처리 과정과 오류 내용이 여기에 표시됩니다.",
                ["log_hint"] = "진행 상황을 자세히 보거나 문의할 때만 펼쳐보세요.",
                ["copy_log"] = "로그 복사",
                ["log_copied"] = "처리 로그를 복사했어요.",
                ["ready"] = "준비됐어요",
                ["reading"] = "미디어를 읽고 파형을 그리는 중이에요…",
                ["processing"] = "보컬을 분리하고 가사 타이밍을 맞추는 중이에요…",
                ["cancel"] = "취소",
                ["generate"] = "SRT 생성",
                ["need_media"] = "먼저 영상 또는 음원을 선택해 주세요.",
                ["need_lyrics"] = "먼저 원문 가사를 붙여 넣어 주세요.",
                ["bad_range"] = "파형에서 1초 이상 선택해 주세요.",
                ["done"] = "SRT를 만들었어요.",
                ["cancelled"] = "취소했어요.",
                ["failed"] = "자막 생성에 실패했어요.",
                ["save"] = "자막 파일 저장",
                ["media_file_type"] = "영상 및 오디오",
                ["text_file_type"] = "텍스트 파일",
                ["subtitle_file_type"] = "SubRip 자막",
                ["technical_details"] = "기술 정보는 상세 정보에서 확인해 주세요.",
            },
        };

    public MainWindow() : this(EngineRuntime.Load())
    {
    }

    internal MainWindow(EngineRuntime runtime)
    {
        InitializeComponent();
        _runtime = runtime;
        _engine = new EngineBridge(_runtime);
        _preferencesPath = AppPaths.Preferences;
        _language = LoadLanguage();
        Waveform.SelectionChanged += Waveform_SelectionChanged;
        ApplyLanguage();
    }

    private string Tr(string key) => Text[_language][key];

    private async void ChooseMedia_Click(object? sender, RoutedEventArgs e)
    {
        IReadOnlyList<IStorageFile> files = await StorageProvider.OpenFilePickerAsync(
            new FilePickerOpenOptions
            {
                Title = Tr("choose_media"),
                AllowMultiple = false,
                FileTypeFilter =
                [
                    new FilePickerFileType(Tr("media_file_type"))
                    {
                        Patterns = ["*.mp4", "*.mov", "*.mkv", "*.avi", "*.webm", "*.wav", "*.mp3", "*.m4a", "*.aac", "*.flac", "*.ogg", "*.opus"],
                    },
                    FilePickerFileTypes.All,
                ],
            });
        string? path = files.FirstOrDefault()?.TryGetLocalPath();
        if (path is null)
        {
            return;
        }
        _mediaPath = path;
        MediaNameText.Text = Path.GetFileName(path);
        SetStatusKey("reading");
        ChooseMediaButton.IsEnabled = false;
        try
        {
            WaveformData data = await _engine.ReadWaveformAsync(path, 850, CancellationToken.None);
            Waveform.SetWaveform(data.Duration, data.Peaks);
            FullFileRadio.IsChecked = true;
            UpdateRangeText(0, data.Duration);
            SetStatusKey("ready");
        }
        catch (Exception exception)
        {
            _mediaPath = null;
            MediaNameText.Text = Tr("no_media");
            AppendLog(exception.ToString());
            SetDetailsExpanded(true);
            await ShowMessageAsync(Tr("failed"), Tr("technical_details"));
            SetStatusKey("ready");
        }
        finally
        {
            ChooseMediaButton.IsEnabled = true;
        }
    }

    private async void LoadLyrics_Click(object? sender, RoutedEventArgs e)
    {
        IReadOnlyList<IStorageFile> files = await StorageProvider.OpenFilePickerAsync(
            new FilePickerOpenOptions
            {
                Title = Tr("load"),
                AllowMultiple = false,
                FileTypeFilter = [new FilePickerFileType(Tr("text_file_type")) { Patterns = ["*.txt"] }, FilePickerFileTypes.All],
            });
        string? path = files.FirstOrDefault()?.TryGetLocalPath();
        if (path is not null)
        {
            LyricsBox.Text = await File.ReadAllTextAsync(path, System.Text.Encoding.UTF8);
        }
    }

    private async void Generate_Click(object? sender, RoutedEventArgs e)
    {
        if (_jobCancellation is not null)
        {
            return;
        }
        if (_mediaPath is null)
        {
            await ShowMessageAsync(Tr("media"), Tr("need_media"));
            return;
        }
        string lyrics = LyricsBox.Text?.Trim() ?? "";
        if (lyrics.Length == 0)
        {
            await ShowMessageAsync(Tr("lyrics"), Tr("need_lyrics"));
            return;
        }
        bool selected = SelectionRadio.IsChecked == true;
        if (selected && Waveform.RangeEnd - Waveform.RangeStart < 1)
        {
            await ShowMessageAsync(Tr("media"), Tr("bad_range"));
            return;
        }
        IStorageFile? destination = await StorageProvider.SaveFilePickerAsync(
            new FilePickerSaveOptions
            {
                Title = Tr("save"),
                SuggestedFileName = $"{Path.GetFileNameWithoutExtension(_mediaPath)}-{DateTime.Now:yyyyMMdd-HHmmss}.srt",
                DefaultExtension = "srt",
                FileTypeChoices = [new FilePickerFileType(Tr("subtitle_file_type")) { Patterns = ["*.srt"] }],
            });
        string? output = destination?.TryGetLocalPath();
        if (output is null)
        {
            return;
        }

        int[] holds = [300, 500, 1000, 1500];
        var request = new AlignmentRequest(
            _mediaPath,
            lyrics,
            output,
            ModeBox.SelectedIndex == 0,
            SelectedDevice(),
            selected,
            Waveform.RangeStart,
            Waveform.RangeEnd,
            (int)(MaxCharsInput.Value ?? 30),
            (int)(MaxDurationInput.Value ?? 10),
            holds[Math.Clamp(EndHoldBox.SelectedIndex, 0, holds.Length - 1)]);

        _jobCancellation = new CancellationTokenSource();
        LogBox.Text = "";
        CopyLogButton.IsEnabled = false;
        SetBusy(true);
        SetStatusKey("processing");
        try
        {
            await _engine.RunAlignmentAsync(
                request,
                line => Dispatcher.UIThread.Post(() => AppendLog(line)),
                _jobCancellation.Token);
            SetStatusKey("done", output);
        }
        catch (OperationCanceledException)
        {
            try { File.Delete(output); } catch (IOException) { }
            SetStatusKey("cancelled");
        }
        catch (Exception exception)
        {
            try { File.Delete(output); } catch (IOException) { }
            AppendLog(exception.ToString());
            SetDetailsExpanded(true);
            await ShowMessageAsync(Tr("failed"), Tr("technical_details"));
            SetStatusKey("failed");
        }
        finally
        {
            _jobCancellation.Dispose();
            _jobCancellation = null;
            SetBusy(false);
        }
    }

    private void Cancel_Click(object? sender, RoutedEventArgs e) => _jobCancellation?.Cancel();

    private async void Help_Click(object? sender, RoutedEventArgs e)
    {
        await new HelpWindow(_language).ShowDialog(this);
    }

    private void Details_Click(object? sender, RoutedEventArgs e)
    {
        bool expanded = !DetailsPanel.IsVisible;
        SetDetailsExpanded(expanded);
        if (expanded)
        {
            DispatcherTimer.RunOnce(
                () =>
                {
                    MainScroll.UpdateLayout();
                    MainScroll.ScrollToEnd();
                },
                TimeSpan.FromMilliseconds(75),
                DispatcherPriority.Background);
        }
    }

    private async void CopyLog_Click(object? sender, RoutedEventArgs e)
    {
        string log = LogBox.Text ?? "";
        if (string.IsNullOrWhiteSpace(log) || TopLevel.GetTopLevel(this)?.Clipboard is not { } clipboard)
        {
            return;
        }
        await clipboard.SetTextAsync(log);
        SetStatusKey("log_copied");
    }

    private void Website_Click(object? sender, RoutedEventArgs e) => OpenUrl("https://voiceandfilm.com");

    private void Instagram_Click(object? sender, RoutedEventArgs e) => OpenUrl("https://www.instagram.com/voiceandfilm/");

    private static void OpenUrl(string url)
    {
        try
        {
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        }
        catch (Exception)
        {
            // A missing browser association should never interrupt subtitle work.
        }
    }

    private void English_Click(object? sender, RoutedEventArgs e)
    {
        _language = "en";
        SaveLanguage();
        ApplyLanguage();
    }

    private void Korean_Click(object? sender, RoutedEventArgs e)
    {
        _language = "ko";
        SaveLanguage();
        ApplyLanguage();
    }

    private void Mode_Changed(object? sender, SelectionChangedEventArgs e)
    {
        if (ManualOptions is not null)
        {
            ManualOptions.IsVisible = ModeBox.SelectedIndex == 1;
        }
    }

    private void RangeMode_Changed(object? sender, RoutedEventArgs e)
    {
        if (Waveform is null)
        {
            return;
        }
        if (FullFileRadio.IsChecked == true)
        {
            Waveform.UseFullRange();
            UpdateRangeText(0, Waveform.Duration);
        }
        else
        {
            Waveform.SelectionEnabled = true;
            Waveform.InvalidateVisual();
        }
    }

    private void Waveform_SelectionChanged(object? sender, WaveformSelectionChangedEventArgs e)
    {
        SelectionRadio.IsChecked = true;
        UpdateRangeText(e.Start, e.End);
    }

    private void ApplyLanguage()
    {
        SubtitleText.Text = Tr("subtitle");
        HelpButton.Content = Tr("help");
        SupportLabel.Text = Tr("support");
        MediaHeading.Text = Tr("media");
        MediaDescription.Text = Tr("media_description");
        if (_mediaPath is null) MediaNameText.Text = Tr("no_media");
        ChooseMediaButton.Content = Tr("choose_media");
        FullFileRadio.Content = Tr("full");
        SelectionRadio.Content = Tr("selection");
        RangeHintText.Text = Tr("range_hint");
        LyricsHeading.Text = Tr("lyrics");
        LyricsDescription.Text = Tr("lyrics_description");
        LoadLyricsButton.Content = Tr("load");
        ModeLabel.Text = Tr("mode");
        int selectedMode = Math.Clamp(ModeBox.SelectedIndex, 0, 1);
        ModeBox.SelectedIndex = -1;
        ((ComboBoxItem)ModeBox.Items[0]!).Content = Tr("auto");
        ((ComboBoxItem)ModeBox.Items[1]!).Content = Tr("manual");
        ModeBox.SelectedIndex = selectedMode;
        DeviceLabel.Text = Tr("device");
        int selectedDevice = Math.Max(0, DeviceBox.SelectedIndex);
        DeviceBox.ItemsSource = _runtime.Backend switch
        {
            "cuda" => new[] { Tr("gpu"), Tr("cpu") },
            "mps" => new[] { Tr("metal"), Tr("cpu") },
            _ => new[] { Tr("cpu") },
        };
        DeviceBox.SelectedIndex = Math.Min(
            selectedDevice,
            _runtime.Backend is "cuda" or "mps" ? 1 : 0);
        MaxCharsLabel.Text = Tr("max_chars");
        MaxDurationLabel.Text = Tr("max_seconds");
        EndHoldLabel.Text = Tr("end_hold");
        MaxCharsInput.FormatString = _language == "ko" ? "0 자" : "0 chars";
        MaxDurationInput.FormatString = _language == "ko" ? "0 초" : "0 s";
        string secondsUnit = _language == "ko" ? "초" : "s";
        string[] holdValues = ["0.3", "0.5", "1.0", "1.5"];
        int selectedHold = Math.Clamp(EndHoldBox.SelectedIndex, 0, holdValues.Length - 1);
        EndHoldBox.SelectedIndex = -1;
        for (int index = 0; index < holdValues.Length; index++)
        {
            ((ComboBoxItem)EndHoldBox.Items[index]!).Content = $"{holdValues[index]} {secondsUnit}";
        }
        EndHoldBox.SelectedIndex = selectedHold;
        DetailsTitle.Text = Tr("details");
        LogBox.PlaceholderText = Tr("log_placeholder");
        LogHintText.Text = Tr("log_hint");
        CopyLogButton.Content = Tr("copy_log");
        CancelButton.Content = Tr("cancel");
        GenerateButton.Content = Tr("generate");
        EnglishButton.Classes.Set("active", _language == "en");
        KoreanButton.Classes.Set("active", _language == "ko");
        RefreshStatus();
    }

    private void SetBusy(bool busy)
    {
        GenerateButton.IsVisible = !busy;
        CancelButton.IsVisible = busy;
        Progress.IsVisible = busy;
        ChooseMediaButton.IsEnabled = !busy;
        LoadLyricsButton.IsEnabled = !busy;
    }

    private void SetStatusKey(string key, string? detail = null)
    {
        _statusKey = key;
        _statusDetail = detail;
        RefreshStatus();
    }

    private void RefreshStatus() =>
        StatusText.Text = _statusDetail is null
            ? Tr(_statusKey)
            : $"{Tr(_statusKey)}  {_statusDetail}";

    private void AppendLog(string line)
    {
        LogBox.Text = (LogBox.Text ?? "") + line + Environment.NewLine;
        LogBox.CaretIndex = LogBox.Text.Length;
        CopyLogButton.IsEnabled = true;
    }

    private void SetDetailsExpanded(bool expanded)
    {
        DetailsPanel.IsVisible = expanded;
        DetailsArrow.Text = expanded ? "▴" : "▾";
    }

    private string SelectedDevice() =>
        _runtime.Backend is "cuda" or "mps" && DeviceBox.SelectedIndex == 0
            ? _runtime.Backend
            : "cpu";

    private void UpdateRangeText(double start, double end) =>
        RangeText.Text = $"{FormatTime(start)} — {FormatTime(end)}";

    private static string FormatTime(double seconds)
    {
        TimeSpan time = TimeSpan.FromSeconds(Math.Max(0, seconds));
        return time.TotalHours >= 1
            ? $"{(int)time.TotalHours:00}:{time.Minutes:00}:{time.Seconds:00}.{time.Milliseconds / 10:00}"
            : $"{time.Minutes:00}:{time.Seconds:00}.{time.Milliseconds / 10:00}";
    }

    private string LoadLanguage()
    {
        try
        {
            using JsonDocument document = JsonDocument.Parse(File.ReadAllText(_preferencesPath));
            string? language = document.RootElement.GetProperty("ui_language").GetString();
            return language is "ko" ? "ko" : "en";
        }
        catch (Exception)
        {
            return "en";
        }
    }

    private void SaveLanguage()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(_preferencesPath)!);
        File.WriteAllText(
            _preferencesPath,
            JsonSerializer.Serialize(new Dictionary<string, string> { ["ui_language"] = _language }));
    }

    private async Task ShowMessageAsync(string title, string message)
    {
        var close = new Button { Content = _language == "ko" ? "확인" : "OK", MinWidth = 80 };
        var dialog = new Window
        {
            Title = title,
            Width = 440,
            SizeToContent = SizeToContent.Height,
            CanResize = false,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = Avalonia.Media.Brush.Parse("#F4EFE0"),
            FontFamily = new Avalonia.Media.FontFamily("Segoe UI"),
            FontSize = 12,
            Content = new StackPanel
            {
                Margin = new Thickness(18),
                Spacing = 14,
                Children =
                {
                    new TextBlock { Text = message, TextWrapping = Avalonia.Media.TextWrapping.Wrap },
                    close,
                },
            },
        };
        close.Click += (_, _) => dialog.Close();
        await dialog.ShowDialog(this);
    }
}
