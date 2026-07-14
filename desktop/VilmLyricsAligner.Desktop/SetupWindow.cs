using System.Diagnostics;
using System.Text;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Layout;
using Avalonia.Media;
using Avalonia.Threading;

namespace VilmLyricsAligner.Desktop;

internal sealed class SetupWindow : Window
{
    private readonly Action _onInstalled;
    private readonly TextBlock _status;
    private readonly ProgressBar _progress;
    private readonly TextBox _log;
    private readonly CheckBox _resolveOption;
    private readonly Button _installButton;
    private readonly CancellationTokenSource _cancellation = new();

    public SetupWindow(Action onInstalled, string? startupError = null)
    {
        _onInstalled = onInstalled;
        Title = "Vilm Lyrics Aligner Setup";
        Width = 560;
        Height = 540;
        MinWidth = 520;
        MinHeight = 500;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        Background = Brush.Parse("#F2E9D2");
        FontFamily = new FontFamily("Segoe UI, Helvetica Neue, Apple SD Gothic Neo");

        bool resolveDetected = IsResolveInstalled();
        _status = new TextBlock
        {
            Text = startupError is null
                ? "Ready to prepare the private AI runtime."
                : "The private AI runtime needs to be installed or repaired.",
            FontWeight = FontWeight.SemiBold,
            TextWrapping = TextWrapping.Wrap,
        };
        _progress = new ProgressBar
        {
            Minimum = 0,
            Maximum = 100,
            Height = 10,
            Value = 0,
        };
        _log = new TextBox
        {
            IsReadOnly = true,
            AcceptsReturn = true,
            TextWrapping = TextWrapping.Wrap,
            MinHeight = 150,
            FontFamily = new FontFamily("Menlo, Consolas, monospace"),
            FontSize = 11,
        };
        _resolveOption = new CheckBox
        {
            Content = resolveDetected
                ? "Install DaVinci Resolve Studio integration (recommended)"
                : "DaVinci Resolve Studio integration (Resolve was not detected)",
            IsChecked = resolveDetected,
            IsEnabled = resolveDetected,
        };
        _installButton = new Button
        {
            Content = "Install",
            HorizontalAlignment = HorizontalAlignment.Right,
            MinWidth = 120,
            Padding = new Thickness(16, 7),
            FontWeight = FontWeight.Bold,
        };
        _installButton.Click += async (_, _) => await InstallAsync();
        Closed += (_, _) => _cancellation.Cancel();

        var header = new StackPanel
        {
            Spacing = 4,
            Children =
            {
                new TextBlock
                {
                    Text = "Vilm Lyrics Aligner",
                    FontSize = 25,
                    FontWeight = FontWeight.Bold,
                },
                new TextBlock
                {
                    Text = "Apple silicon setup",
                    FontSize = 13,
                    Foreground = Brush.Parse("#7A6B55"),
                    FontWeight = FontWeight.SemiBold,
                },
            },
        };

        var card = new Border
        {
            Background = Brush.Parse("#FAF8F2"),
            BorderBrush = Brush.Parse("#C4B69C"),
            BorderThickness = new Thickness(2),
            Padding = new Thickness(18),
            Child = new StackPanel
            {
                Spacing = 12,
                Children =
                {
                    new TextBlock
                    {
                        Text = "The app installs its own Python, PyTorch, and AI models. It does not modify system Python or other projects.",
                        TextWrapping = TextWrapping.Wrap,
                        FontWeight = FontWeight.SemiBold,
                    },
                    new TextBlock
                    {
                        Text = "Allow roughly 4–6 GB of free space. The first setup can take 10–30 minutes depending on your connection.",
                        TextWrapping = TextWrapping.Wrap,
                        Foreground = Brush.Parse("#7A6B55"),
                        FontWeight = FontWeight.SemiBold,
                    },
                    _resolveOption,
                    _status,
                    _progress,
                    _log,
                    _installButton,
                },
            },
        };

        Content = new Grid
        {
            Margin = new Thickness(20),
            RowDefinitions = new RowDefinitions("Auto,14,*"),
            Children = { header, card },
        };
        Grid.SetRow(header, 0);
        Grid.SetRow(card, 2);
    }

    private static bool IsResolveInstalled() =>
        Directory.Exists("/Applications/DaVinci Resolve/DaVinci Resolve.app")
        || Directory.Exists("/Applications/DaVinci Resolve.app");
    private async Task InstallAsync()
    {
        _installButton.IsEnabled = false;
        _resolveOption.IsEnabled = false;
        _log.Text = "";
        try
        {
            string resources = Path.GetFullPath(
                Path.Combine(AppContext.BaseDirectory, "..", "Resources"));
            string script = Path.Combine(resources, "install-runtime.sh");
            string payload = AppPaths.FindBundledPayload();
            if (!File.Exists(script) || !Directory.Exists(payload))
            {
                throw new FileNotFoundException(
                    "The macOS installation payload is incomplete. Reinstall the application.");
            }

            var start = new ProcessStartInfo("/bin/bash")
            {
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8,
                CreateNoWindow = true,
            };
            start.ArgumentList.Add(script);
            start.ArgumentList.Add(payload);
            start.ArgumentList.Add(AppPaths.Root);
            start.ArgumentList.Add(_resolveOption.IsChecked == true ? "1" : "0");
            start.ArgumentList.Add(resources);

            using var process = new Process { StartInfo = start };
            process.Start();
            using CancellationTokenRegistration registration = _cancellation.Token.Register(() =>
            {
                try { if (!process.HasExited) process.Kill(true); }
                catch (InvalidOperationException) { }
            });
            Task stdout = PumpAsync(process.StandardOutput, false, _cancellation.Token);
            Task stderr = PumpAsync(process.StandardError, true, _cancellation.Token);
            await process.WaitForExitAsync(_cancellation.Token);
            await Task.WhenAll(stdout, stderr);
            if (process.ExitCode != 0)
            {
                throw new InvalidOperationException(
                    "Setup did not finish. Review the details above and try again.");
            }

            _ = EngineRuntime.Load();
            _status.Text = "Installation complete.";
            _progress.Value = 100;
            _onInstalled();
            Close();
        }
        catch (OperationCanceledException)
        {
            _status.Text = "Setup cancelled.";
        }
        catch (Exception exception)
        {
            AppendLog(exception.Message, true);
            _status.Text = "Setup failed. Review the details and try again.";
            _installButton.IsEnabled = true;
            _resolveOption.IsEnabled = IsResolveInstalled();
        }
    }

    private async Task PumpAsync(
        StreamReader reader,
        bool isError,
        CancellationToken cancellationToken)
    {
        while (await reader.ReadLineAsync(cancellationToken) is { } line)
        {
            Dispatcher.UIThread.Post(() => HandleLine(line, isError));
        }
    }

    private void HandleLine(string line, bool isError)
    {
        const string marker = "::progress::";
        if (line.StartsWith(marker, StringComparison.Ordinal))
        {
            string[] parts = line[marker.Length..].Split("::", 2);
            if (parts.Length == 2 && double.TryParse(parts[0], out double value))
            {
                _progress.Value = value;
                _status.Text = parts[1];
                return;
            }
        }
        AppendLog(line.StartsWith("::error::", StringComparison.Ordinal)
            ? line[9..]
            : line, isError);
    }

    private void AppendLog(string line, bool isError)
    {
        if (string.IsNullOrWhiteSpace(line)) return;
        _log.Text = (_log.Text ?? "") + (isError ? "! " : "") + line + Environment.NewLine;
        _log.CaretIndex = _log.Text.Length;
    }
}
