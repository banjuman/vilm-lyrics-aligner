import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_SOURCE = PROJECT_ROOT / "installer" / "windows" / "Setup" / "Program.cs"


class WindowsInstallerSourceTests(unittest.TestCase):
    def test_installer_records_verified_runtime_backend(self):
        source = PROGRAM_SOURCE.read_text(encoding="utf-8")
        self.assertIn('string installedBackend = cudaReady ? "cuda" : "cpu";', source)
        self.assertIn('["backend"] = installedBackend', source)

    def test_installer_uses_blackwell_runtime_and_executes_a_cuda_kernel(self):
        source = PROGRAM_SOURCE.read_text(encoding="utf-8")
        self.assertIn("https://download.pytorch.org/whl/cu128", source)
        self.assertNotIn("https://download.pytorch.org/whl/cu126", source)
        self.assertIn("torch.ones(1, device=device) * 2", source)
        self.assertIn("torch.cuda.synchronize(device)", source)
        self.assertIn("torch.cuda.get_device_capability(0)", source)
        self.assertIn("CUDA tensor validation failed", source)
        self.assertIn("CpuTorchIndex", source)

    def test_installer_registers_vilm_panel_and_removes_legacy_entry(self):
        source = PROGRAM_SOURCE.read_text(encoding="utf-8")
        self.assertIn('Path.Combine(pluginDir, "Vilm Lyrics Aligner.py")', source)
        self.assertIn('Path.Combine(pluginDir, "LyricsAligner.py")', source)
        self.assertIn("File.Delete(legacyPluginPath)", source)

    def test_desktop_is_default_and_resolve_is_optional(self):
        source = PROGRAM_SOURCE.read_text(encoding="utf-8")
        self.assertIn("Desktop app will be installed", source)
        self.assertIn("bool installResolve = _resolveOption.Checked;", source)
        self.assertIn("if (installResolve)", source)
        self.assertIn('Path.Combine(appDir, "desktop", "VilmLyricsAligner.exe")', source)
        self.assertIn("CreateStartMenuShortcut(desktopExe, appDir)", source)

    def test_desktop_launcher_is_native_and_console_free(self):
        source = PROGRAM_SOURCE.read_text(encoding="utf-8")
        self.assertIn("shortcut.TargetPath = launcher", source)
        self.assertIn("_installedLauncher = desktopExe", source)
        self.assertNotIn("launch.vbs", source)
        self.assertNotIn("wscript.exe", source)

    def test_reinstall_replaces_only_the_private_runtime(self):
        source = PROGRAM_SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            "ResetPrivateRuntime(appRoot, appDir, toolsDir, pythonDir, venvDir);",
            source,
        )
        self.assertNotIn(
            "ResetPrivateRuntime(appRoot, appDir, toolsDir, pythonDir, venvDir, cacheDir)",
            source,
        )
        self.assertIn("Refusing to replace an unsafe runtime path", source)
        self.assertNotIn('Path.Combine(appRoot, "models")', source)

    def test_network_steps_retry_and_reuse_verified_downloads(self):
        source = PROGRAM_SOURCE.read_text(encoding="utf-8")

        self.assertIn("NetworkRetryDelays", source)
        self.assertIn("TimeSpan.FromSeconds(5)", source)
        self.assertIn("TimeSpan.FromSeconds(10)", source)
        self.assertIn("TimeSpan.FromSeconds(20)", source)
        self.assertIn('"Private Python download"', source)
        self.assertIn('"PyTorch runtime download"', source)
        self.assertIn('"Python dependency download"', source)
        self.assertIn('"AI model download"', source)
        self.assertIn("RunNetworkStepWithRetryAsync", source)
        self.assertIn("Using the verified uv download from the previous setup attempt", source)
        self.assertIn("File.Move(partialPath, zipPath, true)", source)
        self.assertIn("cached files will be reused", source)
        self.assertIn("process.Kill(entireProcessTree: true)", source)

    def test_uv_download_is_version_and_hash_pinned(self):
        source = PROGRAM_SOURCE.read_text(encoding="utf-8")

        self.assertIn('UvVersion = "0.11.28"', source)
        self.assertIn(
            "0A23463216D09C6A72FF80EF5DC5A795F07DC1575CB84D24596C2F124A441B7B",
            source,
        )
        self.assertIn("SHA256.HashDataAsync", source)
        self.assertIn("StringComparison.OrdinalIgnoreCase", source)
        self.assertLess(
            source.index("SHA256.HashDataAsync"),
            source.index("ZipFile.ExtractToDirectory(zipPath"),
        )

    def test_resolve_python_is_bundled_verified_and_installed_conditionally(self):
        source = PROGRAM_SOURCE.read_text(encoding="utf-8")
        build = (PROJECT_ROOT / "installer" / "windows" / "build-installer.ps1").read_text(
            encoding="utf-8"
        )
        project = (
            PROJECT_ROOT / "installer" / "windows" / "Setup" / "LyricsAligner.Setup.csproj"
        ).read_text(encoding="utf-8")

        self.assertIn('ResolvePythonVersion = "3.12.10"', source)
        self.assertIn(
            "67B5635E80EA51072B87941312D00EC8927C4DB9BA18938F7AD2D27B328B95FB",
            source,
        )
        self.assertIn("FindResolvePython312()", source)
        self.assertIn("RegistryHive.CurrentUser", source)
        self.assertIn("RegistryHive.LocalMachine", source)
        self.assertIn("InstallResolvePythonAsync(appRoot", source)
        self.assertIn('"InstallAllUsers=1"', source)
        self.assertIn('"PrependPath=0"', source)
        self.assertNotIn("PYTHONHOME", source)
        self.assertIn("python-3.12.10-amd64.exe", project)
        self.assertIn("www.python.org/ftp/python", build)
        self.assertIn("Get-AuthenticodeSignature", build)
        self.assertIn("Python Software Foundation", build)


if __name__ == "__main__":
    unittest.main()
