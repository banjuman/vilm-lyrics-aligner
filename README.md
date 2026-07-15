# Vilm Lyrics Aligner

Vilm Lyrics Aligner creates editorially timed SRT subtitles from original lyrics and matching audio or video. It is made for live singing, mixed Korean/English lyrics, and recordings where ordinary dictation often gets the timing wrong.

> The lyrics you provide are always the subtitle text source. Audio recognition is used for timing evidence only; it never silently rewrites your words.

[Website & downloads](https://voiceandfilm.com) · [Latest source release](https://github.com/banjuman/vilm-lyrics-aligner/releases/latest) · [English guide](docs/USER_GUIDE.en.md) · [한국어 가이드](docs/USER_GUIDE.ko.md)

## What it does

- Separates vocals from accompaniment before alignment.
- Uses multilingual Whisper timing evidence for Korean/English code-switching.
- Keeps the supplied lyrics and source order intact.
- Creates line-level cues suitable for ordinary subtitles and editorial timing.
- Supports full-file processing or a selected waveform range with its original time offset preserved.
- Offers a standalone desktop app and an optional DaVinci Resolve Studio panel.

## Supported platforms

| Surface | Windows | Apple silicon macOS |
| --- | --- | --- |
| Standalone desktop app | Windows 10/11, NVIDIA CUDA or CPU | macOS 14+, Apple GPU (Metal) or CPU |
| DaVinci Resolve panel | Resolve Studio | Resolve Studio |
| Other editors | Import the generated SRT | Import the generated SRT |

The Resolve panel is optional and requires DaVinci Resolve Studio. The standalone app works with DaVinci Resolve Free and other editors that can import SRT.

## Quick start

1. Download the installer from the [Vilm website](https://voiceandfilm.com).
2. Open a matching video or audio file.
3. Paste the complete lyrics, or load a TXT file.
4. Choose the whole file or drag over only the section you need.
5. Generate the SRT and import it into your editor.

For Resolve Studio, install the optional workflow panel, restart Resolve, open **Workspace → Workflow Integrations → Vilm Lyrics Aligner**, and generate subtitles directly from the current timeline or its In/Out range.

## Auto and Manual modes

- **Auto mode** is the recommended starting point. Line breaks are treated as strong hints, while clear pauses and text length help refine cue boundaries.
- **Manual (advanced) mode** treats each non-empty lyric line as an intentional cue and exposes character, duration, and ending-hold controls.
- A standalone parenthesized line such as `(hmm)` can reserve a non-displayed vocal section for alignment in Manual mode.

The defaults aim for cues below roughly 30 characters and 10 seconds. Singing is expressive: melisma, humming, ad-libs, reordered lyrics, and very soft vocals can still require a small manual correction.

## Installation notes

The installer creates a private Python/PyTorch/AI runtime and does not modify other project environments. The first setup can require several gigabytes of disk space and an internet connection while runtime packages and models are prepared.

- Windows uses verified CUDA-enabled PyTorch when a compatible NVIDIA runtime is available, with CPU fallback.
- Apple silicon macOS uses Whisper through Apple Metal (MPS) and CPU Demucs for the initial release, with CPU fallback.
- Temporary media and separated stems are removed after processing, failure, or cancellation.
- The optional Resolve integration may install the pinned official Python.org 3.12 runtime required by Resolve's workflow system. Shared Resolve Python is retained when Vilm is uninstalled because other Resolve scripts may use it.

## Limitations and expectations

This is a singing-oriented forced-alignment tool, not a general dictation replacement. It reduces manual timing work; it does not promise frame-perfect results for every performance. When the supplied lyrics differ structurally from what was sung, or when a section contains long sustains or humming, review the generated SRT before delivery.

## Development

The source tree contains the Python alignment engine, Avalonia desktop app, Resolve integration, native installers, tests, and platform documentation.

Run the Python tests in an environment containing the project dependencies:

```powershell
python -m unittest discover -s tests -v
```

Build the desktop UI:

```powershell
dotnet build desktop/VilmLyricsAligner.Desktop/VilmLyricsAligner.Desktop.csproj -c Release
```

Build installers only on their native platform:

```powershell
.\installer\windows\build-installer.ps1
```

```bash
chmod +x installer/macos/*.sh
./installer/macos/build-macos.sh
```

Read [the architecture](docs/ARCHITECTURE.md), [the roadmap](ROADMAP.md), and [the contribution guide](CONTRIBUTING.md) before changing alignment behavior. Do not commit client media, lyrics, generated subtitles, model caches, private runtimes, or installer payloads.

## License and notices

Source code is available under the [MIT License](LICENSE). The Vilm name and visual identity are covered by the separate [trademark policy](TRADEMARKS.md). See [third-party notices](THIRD_PARTY_NOTICES.md) for the AI, media, and UI components used by the application.