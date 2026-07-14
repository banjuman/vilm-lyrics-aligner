# Vilm Lyrics Aligner

Vilm Lyrics Aligner turns original lyrics and matching audio/video into editorially timed SRT subtitles. It is designed for live singing, mixed Korean/English lyrics, and instrument-backed recordings where ordinary dictation often gets the words or timing wrong.

The user's lyrics are always the source of truth. Demucs separates vocals, Whisper `small` compares the performance with the supplied text, and the timing pipeline aligns and polishes line-level cues. ASR never silently rewrites the lyrics.

## Two ways to use it

### Desktop app

Use this on Windows or an Apple silicon Mac, including DaVinci Resolve Free and other editors.

1. Open the actual edited video, audio file, or a timeline reference export.
2. Paste the full lyrics.
3. Process the whole file, or drag over the waveform to process only a section.
4. Generate an SRT and import it into the editor. Desktop output includes an invisible zero-origin cue so an NLE keeps the timing before the first real subtitle.

The selected range keeps its original file timecode offset, so the resulting SRT lands at the correct position when the source is a full-timeline reference export.

### DaVinci Resolve Studio integration

The optional Windows/macOS Workflow Integration renders the current timeline or its In/Out range, aligns the lyrics, and imports the SRT directly. This integration requires DaVinci Resolve Studio; the Desktop app does not.

Quick guides: [English](docs/USER_GUIDE.en.md) · [한국어](docs/USER_GUIDE.ko.md)

## Modes

- **Auto mode** uses line breaks as strong hints and adapts cue construction using text length and clear vocal pauses.
- **Manual (advanced)** treats each non-empty lyric line as an intentional cue and exposes maximum characters, duration, and end-hold controls. A standalone parenthesized line such as `(hmm)` can reserve a non-displayed vocal section for alignment.

Defaults target cues below roughly 30 characters and 10 seconds. These are editorial defaults, not promises of frame-perfect automation: melisma, humming, ad-libs, reordered lyrics, and very soft vocals can still need manual correction.

## Windows installer

`installer\windows\dist\VilmLyricsAlignerSetup.exe` is a single-file bootstrap installer that also carries the native Avalonia Desktop UI. It installs an isolated private Python runtime and model environment for the app without modifying `PATH` or `PYTHONHOME`. Desktop is always installed. If DaVinci Resolve Studio is detected, the installer also offers the optional Resolve integration.

Resolve executes Workflow Integration scripts with a discoverable shared Python rather than the app's private AI runtime. When that option is selected, setup checks for a registered Python.org 3.12 installation and, only when absent, installs the bundled official Python 3.12 package before adding the panel. The package is version/hash pinned and publisher-verified during the native Windows build. Shared Resolve Python is intentionally retained when Vilm is removed because other Resolve scripts may depend on it.

NVIDIA systems use the verified CUDA-enabled PyTorch package when it works; other systems use CPU. The installer does not install or replace the system CUDA Toolkit. Models and runtime files live under `%LOCALAPPDATA%\LyricsAligner` and are removed by the registered uninstaller.

The setup executable is compact, but the installed AI runtime is not: expect several gigabytes for Python, PyTorch, Demucs, Whisper, and their model caches. CPU processing is supported but substantially slower.

Build the installer with:

```powershell
.\installer\windows\build-installer.ps1
```

Do not publish an installer until installation, first run, subtitle generation, repair/reinstall, and uninstall have been tested on clean CPU and NVIDIA Windows environments.

## Apple silicon macOS

The macOS target supports Apple silicon and macOS 14 or later. Whisper uses
PyTorch MPS (Apple Metal); Demucs uses the CPU for the initial macOS release to
avoid known compatibility variance in complex-number operations. CPU remains
available as a troubleshooting fallback.

Build the `.app` and DMG on an Apple silicon Mac with:

```bash
chmod +x installer/macos/*.sh
./installer/macos/build-macos.sh
```

The app's first-run screen installs an isolated Python/PyTorch runtime and model
cache under `~/Library/Application Support/Vilm Lyrics Aligner`. It can also
install the optional Resolve Studio integration into Blackmagic Design's
system workflow-plugin folder. See [the macOS build guide](installer/macos/README.md).

## License

Source code is available under the [MIT License](LICENSE). The Vilm name and
visual identity are covered by the separate [trademark policy](TRADEMARKS.md).
See [third-party notices](THIRD_PARTY_NOTICES.md) for the AI, media, and UI
components installed by the application.

## Development

Run the test suite with the project's installed runtime:

```powershell
& "$env:LOCALAPPDATA\LyricsAligner\venv\Scripts\python.exe" -m unittest discover -s tests -v
```

Install the development Resolve panel with:

```powershell
.\scripts\install_resolve_plugin.ps1
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) and [ROADMAP.md](ROADMAP.md) for design constraints and release status.
