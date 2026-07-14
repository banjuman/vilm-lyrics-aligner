# Vilm Lyrics Aligner architecture

## Product contract

- The user-provided lyrics are the source of truth and are never replaced by ASR text.
- The tool aligns known text; it is not an ASR-first subtitle generator.
- Automatic behavior must remain conservative and broadly useful across songs.
- Uncertain comparisons remain in diagnostic JSON instead of changing user output.

## Product surfaces

- **Desktop** is the universal Windows and Apple silicon macOS path. It accepts media directly, can decode only a waveform-selected range, and writes an SRT with the range offset preserved.
- **Resolve Studio integration** is optional. It renders the current timeline or In/Out range and imports the resulting SRT directly.
- Both surfaces invoke the same Python processing package. The Desktop frontend is a compact Avalonia/.NET application; the AI engine remains an isolated Python child process so the UI can stay responsive and cancel the complete process tree.

## Processing pipeline

1. The Desktop app decodes the selected file range, or the Resolve panel validates the selected In/Out marks, converts Resolve's timeline-relative mark values to absolute Deliver frames, then Resolve renders the chosen
   range. Audio-only formats are attempted first; QuickTime is the fallback.
2. FFmpeg-compatible decoding converts the render to a temporary mono WAV. For an In/Out job, transcript comparison locates the continuous matching span in the full supplied lyrics; only that span proceeds to forced alignment.
3. Demucs `htdemucs` separates vocals from the accompaniment.
4. Whisper `small` through stable-ts performs transcription and known-text
   alignment. The transcript supplies anchors and mismatch evidence; output text
   always comes from the user's lyrics.
5. Custom matching preserves source order and compares local ASR windows with
   the full-song alignment.
6. Vocal activity and transition rules refine starts, sustained endings, maximum
   duration and the visual gap between adjacent cues.
7. Desktop work runs in a cancellable child process. Resolve rendering, the external alignment subprocess wait, and SRT import are orchestrated synchronously from Resolve's UI thread. Resolve's embedded UIDispatcher prevents the earlier Python worker from making reliable progress, so the panel currently favors completion over background cancellation. A future standalone app process can restore responsive progress and cancellation. Timeline In/Out marks are snapshotted and restored around temporary render settings.
8. The SRT is imported without deleting existing subtitle items.

## Modes and line breaks

- Auto mode treats line breaks as strong hints, but may split a long/slow line or
  merge only an obvious display wrap when audio evidence supports it.
- Manual mode treats line breaks as cue boundaries. A standalone parenthesized
  line is a hidden alignment cue for humming or another non-lyrical vocal.

## Language model

One multilingual Whisper `small` checkpoint covers the language catalog. `auto`
lets Whisper detect a dominant language during transcription and reuses that
language for known-text alignment. A selected language is a hint, not a claim
that every word in a code-switched song uses that language.

## Device policy

- Windows NVIDIA: the installer validates CUDA and uses it when available.
- Windows without validated CUDA: CPU fallback remains functional.
- Radeon acceleration is not promised by the current Windows runtime because it
  would require a separately tested ROCm package and supported-card matrix.
- Apple silicon macOS: Whisper uses PyTorch MPS (Apple Metal). Demucs stays on
  CPU for the initial macOS release because its complex operations have wider
  backend compatibility variance. CPU remains an explicit troubleshooting path.

The model is fixed. The Desktop/Resolve device control exposes only the accelerator
installed and verified for that platform (CUDA or Metal) plus CPU; unavailable
backends are not shown.

## Files and ownership

- Durable user output: SRT in `Documents\Lyrics Aligner`.
- Diagnostics: JSON under `%LOCALAPPDATA%\LyricsAligner\Diagnostics`, retained
  for 30 days.
- Windows preferences and private runtime: `%LOCALAPPDATA%\LyricsAligner`.
- macOS preferences, private runtime, and models: `~/Library/Application Support/Vilm Lyrics Aligner`.
- The app's AI Python remains private on every platform. Resolve Workflow
  Integration scripts need a Python.org runtime discoverable by Resolve itself;
  installers add the pinned shared Python 3.12 package only when Resolve
  integration is selected and a compatible installation is absent. They do not
  set global `PYTHONHOME` or prepend Python to `PATH`.
- The macOS Resolve panel is installed to Blackmagic Design's system Workflow
  Integration Plugins folder after an explicit administrator prompt.
- Resolve does not execute the app's private AI Python. When the macOS Resolve
  integration is selected, setup installs a pinned, checksum-verified official
  Python.org 3.12 universal2 framework system-wide if it is absent, then installs
  the panel in the same administrator-approved operation. Removal leaves this
  shared framework in place for other Resolve scripts.
- Temporary media, WAV and stems are deleted on completion or failure; stale
  app-owned work directories older than 24 hours are removed on the next launch.
