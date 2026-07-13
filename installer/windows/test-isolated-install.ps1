param(
    [string]$InstallRoot = "C:\tmp\LyricsAligner-Isolated-CPU",
    [ValidateSet("cpu", "cu126")]
    [string]$Backend = "cpu"
)

$ErrorActionPreference = "Stop"
$WindowsRoot = $PSScriptRoot
$PayloadZip = Join-Path $WindowsRoot "Setup\assets\payload.zip"
$ResolvedRoot = [IO.Path]::GetFullPath($InstallRoot)
$AllowedRoot = [IO.Path]::GetFullPath("C:\tmp").TrimEnd('\') + '\'
if (-not $ResolvedRoot.StartsWith($AllowedRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Isolated install root must stay under C:\tmp: $ResolvedRoot"
}
if (-not (Test-Path -LiteralPath $PayloadZip -PathType Leaf)) {
    throw "Build payload first: $PayloadZip"
}

if (Test-Path -LiteralPath $ResolvedRoot) {
    Remove-Item -LiteralPath $ResolvedRoot -Recurse -Force
}
$AppDir = Join-Path $ResolvedRoot "app"
$PythonDir = Join-Path $ResolvedRoot "python"
$VenvDir = Join-Path $ResolvedRoot "venv"
$CacheDir = Join-Path $ResolvedRoot "install-cache"
$ModelDir = Join-Path $ResolvedRoot "models"
New-Item -ItemType Directory -Force -Path $AppDir, $CacheDir, $ModelDir | Out-Null
Expand-Archive -LiteralPath $PayloadZip -DestinationPath $AppDir -Force

$Uv = (Get-Command uv.exe -ErrorAction Stop).Source
$env:UV_PYTHON_INSTALL_DIR = $PythonDir
$env:UV_CACHE_DIR = $CacheDir
$env:UV_NO_MODIFY_PATH = "1"
$env:XDG_CACHE_HOME = $ModelDir
$env:TORCH_HOME = Join-Path $ModelDir "torch"
$env:LYRICS_ALIGNER_DEVICE = if ($Backend -eq "cpu") { "cpu" } else { "cuda" }

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory = $ResolvedRoot)
    Write-Host "> $([IO.Path]::GetFileName($FilePath)) $($Arguments -join ' ')"
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$([IO.Path]::GetFileName($FilePath)) failed with exit code $LASTEXITCODE"
    }
}

Invoke-Checked $Uv @("python", "install", "3.11", "--install-dir", $PythonDir, "--no-bin")
Invoke-Checked $Uv @("venv", $VenvDir, "--python", "3.11", "--managed-python")
$Python = Join-Path $VenvDir "Scripts\python.exe"
$TorchIndex = "https://download.pytorch.org/whl/$Backend"
Invoke-Checked $Uv @(
    "pip", "install", "--python", $Python,
    "torch==2.11.0", "torchaudio==2.11.0", "--index-url", $TorchIndex
)
Invoke-Checked $Uv @(
    "pip", "install", "--python", $Python,
    "-r", (Join-Path $AppDir "requirements-app.txt")
)
Invoke-Checked $Uv @("pip", "install", "--python", $Python, "--no-deps", $AppDir)
Invoke-Checked $Python @("-m", "lyrics_aligner.runtime_setup") $AppDir
Invoke-Checked $Python @("-m", "lyrics_aligner", "--help") $AppDir

$Bytes = (Get-ChildItem -LiteralPath $ResolvedRoot -Recurse -File | Measure-Object Length -Sum).Sum
$Result = [ordered]@{
    ok = $true
    backend = $Backend
    root = $ResolvedRoot
    size_gib = [math]::Round($Bytes / 1GB, 2)
    python = $Python
}
$ResultPath = Join-Path $ResolvedRoot "isolated-install-result.json"
[IO.File]::WriteAllText(
    $ResultPath,
    ($Result | ConvertTo-Json),
    [Text.UTF8Encoding]::new($false)
)
Write-Host ($Result | ConvertTo-Json)
