param(
    [string]$PythonPath = "$env:LOCALAPPDATA\LyricsAligner\venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "Python executable not found: $PythonPath"
}

$PluginRoot = Join-Path $env:PROGRAMDATA "Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Plugins"
$ConfigRoot = Join-Path $env:LOCALAPPDATA "LyricsAligner"
New-Item -ItemType Directory -Force -Path $PluginRoot | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigRoot | Out-Null
$PluginPath = Join-Path $PluginRoot "Vilm Lyrics Aligner.py"
$LegacyPluginPath = Join-Path $PluginRoot "LyricsAligner.py"
Copy-Item -LiteralPath (Join-Path $ProjectRoot "resolve\LyricsAligner.py") -Destination $PluginPath -Force
if (Test-Path -LiteralPath $LegacyPluginPath -PathType Leaf) {
    Remove-Item -LiteralPath $LegacyPluginPath -Force
}

$Backend = "cpu"
try {
    $DetectedBackend = (& $PythonPath -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')").Trim()
    if ($DetectedBackend -eq "cuda") {
        $Backend = "cuda"
    }
} catch {
    $Backend = "cpu"
}

$Config = [ordered]@{
    project_root = $ProjectRoot
    python = (Resolve-Path -LiteralPath $PythonPath).Path
    backend = $Backend
}
$ConfigJson = $Config | ConvertTo-Json
$ConfigPath = Join-Path $ConfigRoot "config.json"
[IO.File]::WriteAllText($ConfigPath, $ConfigJson, [Text.UTF8Encoding]::new($false))

Write-Host "Installed Vilm Lyrics Aligner workflow script."
Write-Host "Restart Resolve, then open Workspace > Workflow Integrations > Vilm Lyrics Aligner."
