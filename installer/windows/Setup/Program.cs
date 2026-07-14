using System.Diagnostics;
using System.IO.Compression;
using Microsoft.Win32;
using System.Reflection;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;

namespace LyricsAligner.Setup;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Contains("--self-test", StringComparer.OrdinalIgnoreCase))
        {
            using Stream? payload = Assembly.GetExecutingAssembly()
                .GetManifestResourceStream("LyricsAligner.payload.zip");
            using Stream? resolvePython = Assembly.GetExecutingAssembly()
                .GetManifestResourceStream("LyricsAligner.python-3.12.10-amd64.exe");
            return payload is { Length: > 0 } && resolvePython is { Length: > 0 } ? 0 : 2;
        }

        ApplicationConfiguration.Initialize();
        Application.Run(new InstallerForm());
        return 0;
    }
}

internal sealed class InstallerForm : Form
{
    private const string UvVersion = "0.11.28";
    private const string UvZipSha256 =
        "0A23463216D09C6A72FF80EF5DC5A795F07DC1575CB84D24596C2F124A441B7B";
    private const string ResolvePythonVersion = "3.12.10";
    private const string ResolvePythonResource = "LyricsAligner.python-3.12.10-amd64.exe";
    private const string ResolvePythonSha256 =
        "67B5635E80EA51072B87941312D00EC8927C4DB9BA18938F7AD2D27B328B95FB";
    private readonly Label _status = new() { AutoSize = false, Dock = DockStyle.Top, Height = 48 };
    private readonly ProgressBar _progress = new() { Dock = DockStyle.Top, Height = 22, Minimum = 0, Maximum = 100 };
    private readonly TextBox _log = new()
    {
        Dock = DockStyle.Fill,
        Multiline = true,
        ReadOnly = true,
        ScrollBars = ScrollBars.Vertical,
        Font = new Font("Consolas", 9),
    };
    private readonly CheckBox _resolveOption = new() { AutoSize = true, Dock = DockStyle.Top };
    private readonly Button _install = new() { Text = "Install", Dock = DockStyle.Bottom, Height = 40 };
    private readonly Button _close = new() { Text = "Close", Dock = DockStyle.Bottom, Height = 36 };
    private readonly CancellationTokenSource _cancellation = new();
    private string? _installedLauncher;

    public InstallerForm()
    {
        Text = "Vilm Lyrics Aligner Setup";
        Width = 720;
        Height = 560;
        StartPosition = FormStartPosition.CenterScreen;

        string? resolvePath = FindResolve();
        _resolveOption.Text = resolvePath is null
            ? "DaVinci Resolve Studio integration (Resolve was not detected)"
            : "Install DaVinci Resolve integration (Studio only, recommended when available)";
        _resolveOption.Checked = resolvePath is not null;
        _resolveOption.Enabled = resolvePath is not null;
        _status.Text = "Desktop app will be installed. Choose the optional Resolve Studio integration, then select Install.";

        Controls.Add(_log);
        Controls.Add(_progress);
        Controls.Add(_status);
        Controls.Add(_resolveOption);
        Controls.Add(_install);
        Controls.Add(_close);
        _install.Click += async (_, _) => await BeginInstallAsync();
        _close.Click += (_, _) => Close();
        FormClosing += (_, _) => _cancellation.Cancel();
    }

    private async Task BeginInstallAsync()
    {
        if (_installedLauncher is not null)
        {
            Process.Start(new ProcessStartInfo(_installedLauncher) { UseShellExecute = true });
            return;
        }
        _install.Enabled = false;
        _resolveOption.Enabled = false;
        await InstallAsync(_cancellation.Token);
    }

    private async Task InstallAsync(CancellationToken cancellationToken)
    {
        try
        {
            bool installResolve = _resolveOption.Checked;
            string? resolvePath = FindResolve();
            if (installResolve && resolvePath is null)
            {
                throw new InvalidOperationException("DaVinci Resolve was not found. Install the Desktop app without the Resolve integration.");
            }
            SetStage(2, "Preparing Vilm Lyrics Aligner Desktop…");
            if (resolvePath is not null) Log($"Resolve: {resolvePath}");

            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string appRoot = Path.Combine(localAppData, "LyricsAligner");
            string appDir = Path.Combine(appRoot, "app");
            string toolsDir = Path.Combine(appRoot, "tools");
            string pythonDir = Path.Combine(appRoot, "python");
            string venvDir = Path.Combine(appRoot, "venv");
            string cacheDir = Path.Combine(appRoot, "install-cache");
            Directory.CreateDirectory(appRoot);
            ResetPrivateRuntime(appRoot, appDir, toolsDir, pythonDir, venvDir, cacheDir);
            Directory.CreateDirectory(toolsDir);
            Directory.CreateDirectory(cacheDir);

            SetStage(8, "Installing application files…");
            ExtractPayload(appDir);

            SetStage(14, "Preparing the private application runtime…");
            string uvPath = Path.Combine(toolsDir, "uv.exe");
            if (!File.Exists(uvPath))
            {
                await DownloadUvAsync(uvPath, cancellationToken);
            }

            var environment = new Dictionary<string, string?>
            {
                ["UV_PYTHON_INSTALL_DIR"] = pythonDir,
                ["UV_CACHE_DIR"] = cacheDir,
                ["UV_NO_MODIFY_PATH"] = "1",
            };

            SetStage(22, "Preparing private Python 3.11…");
            await RunAsync(
                uvPath,
                ["python", "install", "3.11", "--install-dir", pythonDir, "--no-bin"],
                appRoot,
                environment,
                cancellationToken);

            SetStage(30, "Creating an isolated runtime…");
            await RunAsync(
                uvPath,
                ["venv", venvDir, "--python", "3.11", "--managed-python"],
                appRoot,
                environment,
                cancellationToken);
            string pythonExe = Path.Combine(venvDir, "Scripts", "python.exe");

            bool hasNvidia = await DetectNvidiaAsync(cancellationToken);
            string torchIndex = hasNvidia
                ? "https://download.pytorch.org/whl/cu126"
                : "https://download.pytorch.org/whl/cpu";
            SetStage(40, hasNvidia
                ? "Installing the NVIDIA GPU AI runtime…"
                : "Installing the CPU AI runtime…");
            await InstallTorchAsync(
                uvPath, pythonExe, torchIndex, appRoot, environment, cancellationToken);

            bool cudaReady = hasNvidia
                && await VerifyCudaAsync(pythonExe, appRoot, cancellationToken);
            if (hasNvidia && !cudaReady)
            {
                Log("CUDA validation failed. Falling back to the CPU runtime.");
                await InstallTorchAsync(
                    uvPath,
                    pythonExe,
                    "https://download.pytorch.org/whl/cpu",
                    appRoot,
                    environment,
                    cancellationToken,
                    reinstall: true);
            }
            string installedBackend = cudaReady ? "cuda" : "cpu";

            SetStage(58, "Installing Vilm Lyrics Aligner components…");
            await RunAsync(
                uvPath,
                ["pip", "install", "--python", pythonExe, "-r", Path.Combine(appDir, "requirements-app.txt")],
                appRoot,
                environment,
                cancellationToken);
            await RunAsync(
                uvPath,
                ["pip", "install", "--python", pythonExe, "--no-deps", appDir],
                appRoot,
                environment,
                cancellationToken);

            SetStage(74, "Downloading AI models and validating the runtime…");
            await RunAsync(
                pythonExe,
                ["-m", "lyrics_aligner.runtime_setup"],
                appDir,
                null,
                cancellationToken);

            if (installResolve)
            {
                SetStage(84, "Preparing Python for DaVinci Resolve integration...");
                string? resolvePython = FindResolvePython312();
                if (resolvePython is null)
                {
                    await InstallResolvePythonAsync(appRoot, cancellationToken);
                    resolvePython = FindResolvePython312();
                }
                if (resolvePython is null)
                {
                    throw new InvalidOperationException("Python 3.12 was installed but DaVinci Resolve cannot discover it.");
                }
                Log($"Resolve Python: {resolvePython}");
            }

            string pluginDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
                "Blackmagic Design", "DaVinci Resolve", "Support", "Workflow Integration Plugins");
            string pluginPath = Path.Combine(pluginDir, "Vilm Lyrics Aligner.py");
            string legacyPluginPath = Path.Combine(pluginDir, "LyricsAligner.py");
            if (installResolve)
            {
                SetStage(92, "Installing DaVinci Resolve Studio integration…");
                Directory.CreateDirectory(pluginDir);
                File.Copy(
                    Path.Combine(appDir, "resolve", "LyricsAligner.py"),
                    pluginPath,
                    true);
                if (File.Exists(legacyPluginPath)) File.Delete(legacyPluginPath);
            }
            else
            {
                if (File.Exists(pluginPath)) File.Delete(pluginPath);
                if (File.Exists(legacyPluginPath)) File.Delete(legacyPluginPath);
            }

            string configPath = Path.Combine(appRoot, "config.json");
            var config = new Dictionary<string, string>
            {
                ["project_root"] = appDir,
                ["python"] = pythonExe,
                ["backend"] = installedBackend,
            };
            await File.WriteAllTextAsync(
                configPath,
                JsonSerializer.Serialize(config, new JsonSerializerOptions { WriteIndented = true }),
                new UTF8Encoding(false),
                cancellationToken);

            string desktopExe = Path.Combine(appDir, "desktop", "VilmLyricsAligner.exe");
            if (!File.Exists(desktopExe))
            {
                throw new InvalidOperationException("The Vilm Lyrics Aligner Desktop app was not installed.");
            }
            CreateStartMenuShortcut(desktopExe, appDir);
            _installedLauncher = desktopExe;

            TryDeleteDirectory(cacheDir);
            SetStage(100, "Installation complete. Vilm Lyrics Aligner Desktop is ready.");
            Log(installResolve
                ? "Desktop and DaVinci Resolve Studio integration installed."
                : "Desktop app installed.");
            _install.Text = "Open Vilm Lyrics Aligner";
            _install.Enabled = true;
        }
        catch (OperationCanceledException)
        {
            SetStage(_progress.Value, "Installation cancelled.");
            _install.Enabled = true;
        }
        catch (Exception exc)
        {
            Log(exc.ToString());
            SetStage(_progress.Value, $"Installation failed: {exc.Message}");
            _install.Enabled = true;
        }
    }

    private static void CreateStartMenuShortcut(string launcher, string workingDirectory)
    {
        string programs = Environment.GetFolderPath(Environment.SpecialFolder.Programs);
        string shortcutPath = Path.Combine(programs, "Vilm Lyrics Aligner.lnk");
        Type shellType = Type.GetTypeFromProgID("WScript.Shell")
            ?? throw new InvalidOperationException("Windows shortcut service is unavailable.");
        dynamic shell = Activator.CreateInstance(shellType)
            ?? throw new InvalidOperationException("Could not create Windows shortcut service.");
        dynamic shortcut = shell.CreateShortcut(shortcutPath);
        shortcut.TargetPath = launcher;
        shortcut.Arguments = "";
        shortcut.WorkingDirectory = workingDirectory;
        shortcut.Description = "Vilm Lyrics Aligner Desktop";
        shortcut.Save();
    }

    private static string? FindResolve()
    {
        string candidate = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            "Blackmagic Design", "DaVinci Resolve", "Resolve.exe");
        return File.Exists(candidate) ? candidate : null;
    }

    private static string? FindResolvePython312()
    {
        foreach (RegistryHive hive in new[] { RegistryHive.CurrentUser, RegistryHive.LocalMachine })
        {
            try
            {
                using RegistryKey baseKey = RegistryKey.OpenBaseKey(hive, RegistryView.Registry64);
                using RegistryKey? installKey = baseKey.OpenSubKey(
                    @"SOFTWARE\Python\PythonCore\3.12\InstallPath");
                string? installPath = installKey?.GetValue(null)?.ToString();
                if (string.IsNullOrWhiteSpace(installPath)) continue;

                string pythonExe = Path.Combine(installPath, "python.exe");
                string stableDll = Path.Combine(installPath, "python3.dll");
                if (File.Exists(pythonExe) && File.Exists(stableDll)) return pythonExe;
            }
            catch (Exception exc) when (exc is IOException or UnauthorizedAccessException)
            {
                // Try the next registry hive.
            }
        }
        return null;
    }

    private async Task InstallResolvePythonAsync(
        string workingDirectory,
        CancellationToken cancellationToken)
    {
        string installerPath = Path.Combine(
            Path.GetTempPath(),
            $"Vilm-Resolve-Python-{ResolvePythonVersion}-{Guid.NewGuid():N}.exe");
        try
        {
            await using (Stream embedded = Assembly.GetExecutingAssembly()
                .GetManifestResourceStream(ResolvePythonResource)
                ?? throw new InvalidOperationException("The bundled Resolve Python installer is missing."))
            await using (FileStream destination = File.Create(installerPath))
            {
                await embedded.CopyToAsync(destination, cancellationToken);
            }

            string actualHash;
            await using (FileStream installer = File.OpenRead(installerPath))
            {
                actualHash = Convert.ToHexString(
                    await SHA256.HashDataAsync(installer, cancellationToken));
            }
            if (!string.Equals(actualHash, ResolvePythonSha256, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException(
                    $"Resolve Python installer verification failed. expected={ResolvePythonSha256}, actual={actualHash}");
            }

            using X509Certificate signer = X509Certificate.CreateFromSignedFile(installerPath);
            if (!signer.Subject.Contains("Python Software Foundation", StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException(
                    $"Resolve Python installer publisher is unexpected: {signer.Subject}");
            }

            Log($"Installing shared Python {ResolvePythonVersion} for DaVinci Resolve...");
            await RunAsync(
                installerPath,
                [
                    "/quiet",
                    "InstallAllUsers=1",
                    "Include_launcher=0",
                    "InstallLauncherAllUsers=0",
                    "AssociateFiles=0",
                    "Shortcuts=0",
                    "Include_doc=0",
                    "Include_test=0",
                    "Include_tcltk=0",
                    "Include_pip=0",
                    "PrependPath=0",
                ],
                workingDirectory,
                null,
                cancellationToken);
        }
        finally
        {
            if (File.Exists(installerPath)) File.Delete(installerPath);
        }
    }

    private static void ResetPrivateRuntime(
        string appRoot,
        params string[] runtimeDirectories)
    {
        if (!string.Equals(
            Path.GetFileName(Path.TrimEndingDirectorySeparator(appRoot)),
            "LyricsAligner",
            StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException("Refusing to replace an unsafe runtime path.");
        }
        foreach (string directory in runtimeDirectories)
        {
            if (Directory.Exists(directory)) Directory.Delete(directory, true);
        }
        string configPath = Path.Combine(appRoot, "config.json");
        if (File.Exists(configPath)) File.Delete(configPath);
    }

    private static void ExtractPayload(string appDir)
    {
        if (Directory.Exists(appDir))
        {
            Directory.Delete(appDir, true);
        }
        Directory.CreateDirectory(appDir);
        using Stream payload = Assembly.GetExecutingAssembly()
            .GetManifestResourceStream("LyricsAligner.payload.zip")
            ?? throw new InvalidOperationException("The installation payload is missing.");
        using var archive = new ZipArchive(payload, ZipArchiveMode.Read);
        archive.ExtractToDirectory(appDir, true);
    }

    private async Task DownloadUvAsync(string uvPath, CancellationToken cancellationToken)
    {
        string url = $"https://github.com/astral-sh/uv/releases/download/{UvVersion}/uv-x86_64-pc-windows-msvc.zip";
        string zipPath = Path.Combine(Path.GetDirectoryName(uvPath)!, "uv.zip");
        using var client = new HttpClient();
        Log($"Download: {url}");
        await using (Stream source = await client.GetStreamAsync(url, cancellationToken))
        await using (FileStream destination = File.Create(zipPath))
        {
            await source.CopyToAsync(destination, cancellationToken);
        }

        string actualHash;
        await using (FileStream downloadedZip = File.OpenRead(zipPath))
        {
            actualHash = Convert.ToHexString(
                await SHA256.HashDataAsync(downloadedZip, cancellationToken));
        }
        if (!string.Equals(actualHash, UvZipSha256, StringComparison.OrdinalIgnoreCase))
        {
            File.Delete(zipPath);
            throw new InvalidOperationException(
                $"uv download integrity check failed. expected={UvZipSha256}, actual={actualHash}");
        }

        ZipFile.ExtractToDirectory(zipPath, Path.GetDirectoryName(uvPath)!, true);
        File.Delete(zipPath);
        if (!File.Exists(uvPath))
        {
            throw new InvalidOperationException("The uv archive did not contain uv.exe.");
        }
    }

    private async Task<bool> DetectNvidiaAsync(CancellationToken cancellationToken)
    {
        try
        {
            ProcessResult result = await RunAsync(
                "nvidia-smi.exe",
                ["--query-gpu=name", "--format=csv,noheader"],
                Environment.CurrentDirectory,
                null,
                cancellationToken,
                throwOnFailure: false);
            bool detected = result.ExitCode == 0 && !string.IsNullOrWhiteSpace(result.StdOut);
            Log(detected ? $"NVIDIA detected: {result.StdOut.Trim()}" : "No NVIDIA CUDA device detected — CPU mode");
            return detected;
        }
        catch
        {
            Log("No NVIDIA CUDA device detected — CPU mode");
            return false;
        }
    }

    private async Task InstallTorchAsync(
        string uvPath,
        string pythonExe,
        string index,
        string workingDirectory,
        IReadOnlyDictionary<string, string?> environment,
        CancellationToken cancellationToken,
        bool reinstall = false)
    {
        var arguments = new List<string>
        {
            "pip", "install", "--python", pythonExe,
            "torch==2.11.0", "torchaudio==2.11.0",
            "--index-url", index,
        };
        if (reinstall)
        {
            arguments.Add("--reinstall");
        }
        await RunAsync(uvPath, arguments, workingDirectory, environment, cancellationToken);
    }

    private async Task<bool> VerifyCudaAsync(
        string pythonExe, string workingDirectory, CancellationToken cancellationToken)
    {
        ProcessResult result = await RunAsync(
            pythonExe,
            ["-c", "import torch; print(torch.cuda.is_available())"],
            workingDirectory,
            null,
            cancellationToken,
            throwOnFailure: false);
        return result.ExitCode == 0 && result.StdOut.Contains("True", StringComparison.OrdinalIgnoreCase);
    }

    private async Task<ProcessResult> RunAsync(
        string executable,
        IReadOnlyCollection<string> arguments,
        string workingDirectory,
        IReadOnlyDictionary<string, string?>? environment,
        CancellationToken cancellationToken,
        bool throwOnFailure = true)
    {
        var start = new ProcessStartInfo(executable)
        {
            WorkingDirectory = workingDirectory,
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
        if (environment is not null)
        {
            foreach ((string key, string? value) in environment)
            {
                start.Environment[key] = value;
            }
        }
        Log($"> {Path.GetFileName(executable)} {string.Join(' ', arguments)}");
        using var process = new Process { StartInfo = start };
        process.Start();
        Task<string> stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        Task<string> stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken);
        string stdout = await stdoutTask;
        string stderr = await stderrTask;
        if (!string.IsNullOrWhiteSpace(stdout)) Log(stdout.Trim());
        if (!string.IsNullOrWhiteSpace(stderr)) Log(stderr.Trim());
        if (throwOnFailure && process.ExitCode != 0)
        {
            throw new InvalidOperationException(
                $"{Path.GetFileName(executable)} failed (code {process.ExitCode})");
        }
        return new ProcessResult(process.ExitCode, stdout, stderr);
    }

    private void SetStage(int percent, string message)
    {
        if (InvokeRequired)
        {
            BeginInvoke(() => SetStage(percent, message));
            return;
        }
        _progress.Value = Math.Clamp(percent, 0, 100);
        _status.Text = message;
    }

    private void Log(string message)
    {
        if (InvokeRequired)
        {
            BeginInvoke(() => Log(message));
            return;
        }
        _log.AppendText(message + Environment.NewLine);
    }

    private static void TryDeleteDirectory(string path)
    {
        try
        {
            if (Directory.Exists(path)) Directory.Delete(path, true);
        }
        catch
        {
            // Installation succeeded; a disposable download cache is not fatal.
        }
    }

    private sealed record ProcessResult(int ExitCode, string StdOut, string StdErr);
}
