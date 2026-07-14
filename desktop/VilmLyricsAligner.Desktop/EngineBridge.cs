using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace VilmLyricsAligner.Desktop;

internal sealed record EngineRuntime(string Python, string ProjectRoot, string Backend, string AppRoot)
{
    public static EngineRuntime Load()
    {
        string appRoot = AppPaths.Root;
        string configPath = AppPaths.Config;
        if (File.Exists(configPath))
        {
            using JsonDocument config = JsonDocument.Parse(File.ReadAllText(configPath));
            JsonElement root = config.RootElement;
            string python = root.GetProperty("python").GetString()
                ?? throw new InvalidOperationException("The configured Python path is empty.");
            string project = root.GetProperty("project_root").GetString()
                ?? throw new InvalidOperationException("The configured project path is empty.");
            if (!File.Exists(python))
            {
                throw new InvalidOperationException("The private Python runtime is missing.");
            }
            if (!Directory.Exists(project))
            {
                throw new InvalidOperationException("The alignment engine files are missing.");
            }
            string backend = root.TryGetProperty("backend", out JsonElement value)
                ? value.GetString() ?? "cpu"
                : "cpu";
            backend = backend.ToLowerInvariant();
            if (backend is not ("cuda" or "mps" or "cpu"))
            {
                backend = "cpu";
            }
            return new EngineRuntime(python, project, backend, appRoot);
        }

        string? developmentRoot = FindProjectRoot(Environment.CurrentDirectory)
            ?? FindProjectRoot(AppContext.BaseDirectory);
        if (developmentRoot is null)
        {
            throw new InvalidOperationException("Vilm Lyrics Aligner engine configuration was not found.");
        }
        return new EngineRuntime("python", developmentRoot, "cpu", appRoot);
    }

    private static string? FindProjectRoot(string start)
    {
        DirectoryInfo? directory = new(start);
        while (directory is not null)
        {
            if (File.Exists(Path.Combine(directory.FullName, "pyproject.toml")))
            {
                return directory.FullName;
            }
            directory = directory.Parent;
        }
        return null;
    }
}

internal sealed record WaveformData(double Duration, IReadOnlyList<double> Peaks);

internal sealed record AlignmentRequest(
    string Media,
    string Lyrics,
    string Output,
    bool Automatic,
    string Device,
    bool SelectedRange,
    double RangeStart,
    double RangeEnd,
    int MaxCharacters,
    int MaxDurationSeconds,
    int EndHoldMilliseconds);

internal sealed class EngineBridge(EngineRuntime runtime)
{
    public async Task<WaveformData> ReadWaveformAsync(
        string media,
        int bins,
        CancellationToken cancellationToken)
    {
        ProcessResult result = await RunAsync(
            ["-m", "lyrics_aligner", "waveform", media, "--bins", bins.ToString()],
            null,
            cancellationToken,
            null);
        if (result.ExitCode != 0)
        {
            throw new InvalidOperationException(result.Error.Trim().Length > 0 ? result.Error.Trim() : result.Output.Trim());
        }
        using JsonDocument document = JsonDocument.Parse(result.Output.Trim());
        JsonElement root = document.RootElement;
        double duration = root.GetProperty("duration").GetDouble();
        double[] peaks = root.GetProperty("peaks").EnumerateArray().Select(item => item.GetDouble()).ToArray();
        return new WaveformData(duration, peaks);
    }

    public async Task RunAlignmentAsync(
        AlignmentRequest request,
        Action<string> onOutput,
        CancellationToken cancellationToken)
    {
        string lyricsPath = Path.Combine(Path.GetTempPath(), $"vilm-lyrics-{Guid.NewGuid():N}.txt");
        string workDirectory = Path.Combine(Path.GetTempPath(), $"lyrics-aligner-{Guid.NewGuid():N}");
        Directory.CreateDirectory(workDirectory);
        try
        {
            await File.WriteAllTextAsync(lyricsPath, request.Lyrics, new System.Text.UTF8Encoding(false), cancellationToken);
            var arguments = new List<string>
            {
                "-m", "lyrics_aligner", "align",
                request.Media, lyricsPath,
                "-o", request.Output,
                "--max-chars", request.MaxCharacters.ToString(),
                "--max-duration-ms", (request.MaxDurationSeconds * 1000).ToString(),
                "--end-pad-ms", request.EndHoldMilliseconds.ToString(),
                "--min-gap-ms", "80",
                "--timeline-anchor",
                "--work-dir", workDirectory,
            };
            if (request.Automatic)
            {
                arguments.Add("--auto-segment");
            }
            if (request.SelectedRange)
            {
                arguments.AddRange([
                    "--range-start", request.RangeStart.ToString("0.######", System.Globalization.CultureInfo.InvariantCulture),
                    "--range-end", request.RangeEnd.ToString("0.######", System.Globalization.CultureInfo.InvariantCulture),
                    "--partial-range",
                ]);
            }
            var environment = new Dictionary<string, string>
            {
                ["LYRICS_ALIGNER_DEVICE"] = request.Device,
            };
            ProcessResult result = await RunAsync(arguments, environment, cancellationToken, onOutput);
            if (result.ExitCode != 0)
            {
                string message = result.Error.Trim().Length > 0 ? result.Error.Trim() : result.Output.Trim();
                throw new InvalidOperationException(message.Length > 0 ? message : "Alignment failed.");
            }
        }
        finally
        {
            try { File.Delete(lyricsPath); } catch (IOException) { }
            try { Directory.Delete(workDirectory, true); } catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
    }

    private async Task<ProcessResult> RunAsync(
        IReadOnlyCollection<string> arguments,
        IReadOnlyDictionary<string, string>? environment,
        CancellationToken cancellationToken,
        Action<string>? onOutput)
    {
        var start = new ProcessStartInfo(runtime.Python)
        {
            WorkingDirectory = runtime.ProjectRoot,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
            CreateNoWindow = true,
        };
        foreach (string argument in arguments)
        {
            start.ArgumentList.Add(argument);
        }
        start.Environment["PYTHONUTF8"] = "1";
        start.Environment["PYTHONIOENCODING"] = "utf-8";
        start.Environment["LYRICS_ALIGNER_APP_ROOT"] = runtime.AppRoot;
        start.Environment["XDG_CACHE_HOME"] = Path.Combine(runtime.AppRoot, "models");
        start.Environment["TORCH_HOME"] = Path.Combine(runtime.AppRoot, "models", "torch");
        if (OperatingSystem.IsMacOS())
        {
            start.Environment["PYTORCH_ENABLE_MPS_FALLBACK"] = "1";
        }
        if (environment is not null)
        {
            foreach ((string key, string value) in environment)
            {
                start.Environment[key] = value;
            }
        }

        using var process = new Process { StartInfo = start };
        process.Start();
        using CancellationTokenRegistration registration = cancellationToken.Register(() =>
        {
            try
            {
                if (!process.HasExited) process.Kill(true);
            }
            catch (InvalidOperationException) { }
        });

        var output = new List<string>();
        var error = new List<string>();
        Task pumpOut = PumpAsync(process.StandardOutput, output, onOutput, cancellationToken);
        Task pumpError = PumpAsync(process.StandardError, error, onOutput, cancellationToken);
        try
        {
            await process.WaitForExitAsync(cancellationToken);
            await Task.WhenAll(pumpOut, pumpError);
        }
        catch (OperationCanceledException)
        {
            try { if (!process.HasExited) process.Kill(true); } catch (InvalidOperationException) { }
            try { await process.WaitForExitAsync(CancellationToken.None); } catch (InvalidOperationException) { }
            throw;
        }
        return new ProcessResult(process.ExitCode, string.Join(Environment.NewLine, output), string.Join(Environment.NewLine, error));
    }

    private static async Task PumpAsync(
        StreamReader reader,
        List<string> destination,
        Action<string>? onOutput,
        CancellationToken cancellationToken)
    {
        while (await reader.ReadLineAsync(cancellationToken) is { } line)
        {
            destination.Add(line);
            onOutput?.Invoke(line);
        }
    }

    private sealed record ProcessResult(int ExitCode, string Output, string Error);
}
