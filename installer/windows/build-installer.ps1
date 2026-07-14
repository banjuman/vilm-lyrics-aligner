param(
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"
$env:AVALONIA_TELEMETRY_OPTOUT = "1"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
$WindowsRoot = $PSScriptRoot
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $WindowsRoot)
$SetupRoot = Join-Path $WindowsRoot "Setup"
$Assets = Join-Path $SetupRoot "assets"
$Stage = Join-Path $WindowsRoot "build\payload"
$DesktopPublish = Join-Path $WindowsRoot "build\desktop"
$DesktopProject = Join-Path $ProjectRoot "desktop\VilmLyricsAligner.Desktop\VilmLyricsAligner.Desktop.csproj"
$PayloadZip = Join-Path $Assets "payload.zip"
$ResolvePythonVersion = "3.12.10"
$ResolvePythonInstaller = Join-Path $Assets "python-$ResolvePythonVersion-amd64.exe"
$ResolvePythonUrl = "https://www.python.org/ftp/python/$ResolvePythonVersion/python-$ResolvePythonVersion-amd64.exe"
$ResolvePythonSha256 = "67B5635E80EA51072B87941312D00EC8927C4DB9BA18938F7AD2D27B328B95FB"
$ResolvePythonPublisher = "Python Software Foundation"
$Output = Join-Path $WindowsRoot "dist"

$ResolvedProject = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\') + '\'
foreach ($Target in @($Stage, $DesktopPublish, $Assets, $Output)) {
    $ResolvedTarget = [IO.Path]::GetFullPath($Target)
    if (-not $ResolvedTarget.StartsWith($ResolvedProject, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Build target escaped the workspace: $ResolvedTarget"
    }
}

if (-not (Test-Path -LiteralPath $ResolvePythonInstaller -PathType Leaf)) {
    $DownloadPath = "$ResolvePythonInstaller.download"
    Remove-Item -LiteralPath $DownloadPath -Force -ErrorAction SilentlyContinue
    Invoke-WebRequest -UseBasicParsing -Uri $ResolvePythonUrl -OutFile $DownloadPath
    Move-Item -LiteralPath $DownloadPath -Destination $ResolvePythonInstaller -Force
}
$ResolvePythonActualHash = (Get-FileHash -LiteralPath $ResolvePythonInstaller -Algorithm SHA256).Hash
if (-not [string]::Equals(
    $ResolvePythonActualHash,
    $ResolvePythonSha256,
    [StringComparison]::OrdinalIgnoreCase)) {
    Remove-Item -LiteralPath $ResolvePythonInstaller -Force
    throw "Resolve Python installer hash verification failed. expected=$ResolvePythonSha256 actual=$ResolvePythonActualHash"
}
$ResolvePythonSignature = Get-AuthenticodeSignature -LiteralPath $ResolvePythonInstaller
if ($ResolvePythonSignature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
    throw "Resolve Python installer signature is invalid: $($ResolvePythonSignature.StatusMessage)"
}
if ($ResolvePythonSignature.SignerCertificate.Subject -notlike "*$ResolvePythonPublisher*") {
    throw "Resolve Python installer publisher is unexpected: $($ResolvePythonSignature.SignerCertificate.Subject)"
}

foreach ($Target in @($Stage, $DesktopPublish, $Output)) {
    if (Test-Path -LiteralPath $Target) {
        Remove-Item -LiteralPath $Target -Recurse -Force
    }
}
New-Item -ItemType Directory -Force -Path $Stage, $DesktopPublish, $Assets, $Output | Out-Null

dotnet publish $DesktopProject `
    -c $Configuration `
    -r win-x64 `
    --self-contained true `
    -o $DesktopPublish
if ($LASTEXITCODE -ne 0) {
    throw "Desktop publish failed with exit code $LASTEXITCODE"
}
$DesktopExe = Join-Path $DesktopPublish "VilmLyricsAligner.exe"
if (-not (Test-Path -LiteralPath $DesktopExe -PathType Leaf)) {
    throw "Desktop output was not created: $DesktopExe"
}

Copy-Item -LiteralPath (Join-Path $ProjectRoot "lyrics_aligner") -Destination $Stage -Recurse
Get-ChildItem -LiteralPath (Join-Path $Stage "lyrics_aligner") -Directory -Filter "__pycache__" -Recurse |
    Remove-Item -Recurse -Force
foreach ($LegacyName in @("qwen.py", "demucs_torchaudio_legacy.py")) {
    $LegacyPath = Join-Path $Stage "lyrics_aligner\backends\$LegacyName"
    if (Test-Path -LiteralPath $LegacyPath) {
        Remove-Item -LiteralPath $LegacyPath -Force
    }
}
New-Item -ItemType Directory -Force -Path (Join-Path $Stage "resolve") | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectRoot "resolve\LyricsAligner.py") -Destination (Join-Path $Stage "resolve\LyricsAligner.py")
Copy-Item -LiteralPath (Join-Path $ProjectRoot "pyproject.toml") -Destination $Stage
Copy-Item -LiteralPath (Join-Path $ProjectRoot "LICENSE") -Destination $Stage
Copy-Item -LiteralPath (Join-Path $ProjectRoot "THIRD_PARTY_NOTICES.md") -Destination $Stage
Copy-Item -LiteralPath (Join-Path $ProjectRoot "TRADEMARKS.md") -Destination $Stage
Copy-Item -LiteralPath (Join-Path $WindowsRoot "..\requirements-app.txt") -Destination $Stage
New-Item -ItemType Directory -Force -Path (Join-Path $Stage "desktop") | Out-Null
Copy-Item -LiteralPath $DesktopExe -Destination (Join-Path $Stage "desktop\VilmLyricsAligner.exe")

if (Test-Path -LiteralPath $PayloadZip) {
    Remove-Item -LiteralPath $PayloadZip -Force
}
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $PayloadZip -CompressionLevel Optimal

dotnet publish (Join-Path $SetupRoot "LyricsAligner.Setup.csproj") `
    -c $Configuration `
    -r win-x64 `
    --self-contained true `
    -p:PublishSingleFile=true `
    -o $Output
if ($LASTEXITCODE -ne 0) {
    throw "dotnet publish failed with exit code $LASTEXITCODE"
}

$Installer = Join-Path $Output "VilmLyricsAlignerSetup.exe"
if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) {
    throw "Installer output was not created: $Installer"
}
$Unexpected = Get-ChildItem -LiteralPath $Output -File | Where-Object Name -ne "VilmLyricsAlignerSetup.exe"
if ($Unexpected) {
    throw "Installer is not a single-file build: $($Unexpected.Name -join ', ')"
}
Write-Host "Built: $Installer"
