from __future__ import annotations

import os
from pathlib import Path


from .platform_paths import managed_runtime_root



def register_windows_uninstaller() -> bool:
    """Register safe removal only for the one-click managed installation."""
    if os.name != "nt":
        return False
    runtime_root = managed_runtime_root()
    if runtime_root is None:
        return False

    try:
        import winreg

        program_data = Path(os.environ["PROGRAMDATA"])
        uninstall_dir = program_data / "LyricsAligner"
        uninstall_dir.mkdir(parents=True, exist_ok=True)
        uninstall_script = uninstall_dir / "uninstall.ps1"
        plugin_path = (
            program_data
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Workflow Integration Plugins"
            / "Vilm Lyrics Aligner.py"
        )
        uninstall_script.write_text(
            _uninstall_script(runtime_root, plugin_path, uninstall_dir),
            encoding="utf-8-sig",
        )

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\LyricsAligner"
        with winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE,
            key_path,
            0,
            winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY,
        ) as key:
            command = (
                f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File '
                f'"{uninstall_script}"'
            )
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Vilm Lyrics Aligner")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Vilm")
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(runtime_root))
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, command)
            winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, command)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        return True
    except (OSError, PermissionError, KeyError):
        # Normal Resolve launches are not elevated. Registration is completed
        # during the elevated one-click installation and is best-effort later.
        return False


def _ps_literal(path: Path) -> str:
    return str(path).replace("'", "''")


def _uninstall_script(runtime_root: Path, plugin_path: Path, uninstall_dir: Path) -> str:
    app = _ps_literal(runtime_root)
    plugin = _ps_literal(plugin_path)
    own_dir = _ps_literal(uninstall_dir)
    return rf"""$ErrorActionPreference = 'Stop'
$Resolve = Get-Process -Name Resolve -ErrorAction SilentlyContinue
if ($Resolve) {{
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        'DaVinci Resolve를 종료한 뒤 다시 제거해 주세요.',
        'Vilm Lyrics Aligner 제거'
    ) | Out-Null
    exit 1
}}

$AppRoot = '{app}'
$PluginPath = '{plugin}'
$LegacyPluginPath = Join-Path (Split-Path -Parent $PluginPath) 'LyricsAligner.py'
$UninstallRoot = '{own_dir}'
if ([IO.Path]::GetFileName($AppRoot) -ne 'LyricsAligner') {{
    throw '안전하지 않은 설치 경로라 제거를 중단했습니다.'
}}

if (Test-Path -LiteralPath $PluginPath) {{
    Remove-Item -LiteralPath $PluginPath -Force
}}
if (Test-Path -LiteralPath $LegacyPluginPath) {{
    Remove-Item -LiteralPath $LegacyPluginPath -Force
}}
$StartMenuShortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'Vilm Lyrics Aligner.lnk'
if (Test-Path -LiteralPath $StartMenuShortcut) {{
    Remove-Item -LiteralPath $StartMenuShortcut -Force
}}
if (Test-Path -LiteralPath $AppRoot) {{
    Remove-Item -LiteralPath $AppRoot -Recurse -Force
}}
Remove-Item -LiteralPath 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\LyricsAligner' -Recurse -Force -ErrorAction SilentlyContinue

$Cleanup = "Start-Sleep -Seconds 2; Remove-Item -LiteralPath '$UninstallRoot' -Recurse -Force"
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
    '-NoProfile', '-WindowStyle', 'Hidden', '-Command', $Cleanup
)
"""
