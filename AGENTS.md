# Vilm Lyrics Aligner contributor guidance

## Product contract

- The supplied lyrics are always the subtitle text source. ASR may compare and
  diagnose, but it must never silently replace the user's words.
- This is a singing-oriented forced-alignment tool, not a general dictation
  rewrite. Preserve mixed-language lyrics and source order.
- Auto mode should remain conservative and broadly useful. Do not add
  song-specific timing heuristics without repeatable evidence across multiple
  recordings.
- Manual mode treats non-empty source lines as intentional cue boundaries and
  may expose editorial timing controls.
- Do not publish real client audio, video, lyrics, diagnostics, or generated
  subtitles in tests or fixtures.

## Supported surfaces

- Windows desktop app: Avalonia, `win-x64`.
- Apple silicon desktop app: Avalonia, `osx-arm64`, macOS 14 or later.
- DaVinci Resolve Studio workflow panel: Windows and macOS.
- NVIDIA uses CUDA when the private runtime verifies it. Apple silicon uses
  MPS for Whisper and CPU for Demucs. All platforms retain a CPU fallback.

## Verification

Run the Python suite with an environment containing the dependencies:

```text
python -m unittest discover -s tests -v
```

Build the desktop UI with telemetry disabled in automated environments:

```text
dotnet build desktop/VilmLyricsAligner.Desktop/VilmLyricsAligner.Desktop.csproj -c Release
```

Build platform packages only on their native OS:

- Windows: `installer/windows/build-installer.ps1`
- Apple silicon macOS: `installer/macos/build-macos.sh`

Keep generated `bin`, `obj`, installer payloads, model caches, media, and local
validation outputs out of Git. Keep English and Korean UI text in sync. Update
the root README, architecture, roadmap, license notices, and platform test plan
when a user-facing contract changes.
