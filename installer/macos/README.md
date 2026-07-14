# Apple silicon macOS build

This target supports Apple silicon only and requires macOS 14 or later. The
standalone app works with any editor that can import SRT. The optional workflow
panel requires DaVinci Resolve Studio.

## Development build on the test Mac

1. Install Xcode Command Line Tools:

   ```bash
   xcode-select --install
   ```

2. Install the .NET 8 SDK for Apple silicon.
3. Clone the repository, then run:

   ```bash
   chmod +x installer/macos/*.sh
   ./installer/macos/build-macos.sh
   ```

4. Open `installer/macos/dist/VilmLyricsAligner-1.0.0-apple-silicon.dmg`, drag
   the app to Applications, and open it. An unsigned development build may need
   **Control-click → Open** the first time.
5. Select **Install** in the first-run window. This creates an isolated runtime
   under `~/Library/Application Support/Vilm Lyrics Aligner`, downloads the AI
   models, verifies Apple Metal, and optionally installs the Resolve Studio
   panel after the normal administrator prompt. If Python.org 3.12 is not
   already installed, the same approval also installs the bundled official
   universal2 runtime that Resolve needs to execute Python workflow panels.
   Setup remains open until the private runtime, shared Resolve runtime, and
   panel have all passed verification. Select **Open Vilm Lyrics Aligner** only
   after the completion message appears, then restart Resolve before opening
   the panel.

The first setup requires an internet connection and roughly 4–6 GB of free
space. The AI runtime remains private and does not modify environments belonging
to other projects. The optional Resolve integration is the only system-wide
Python installation; its pinned Python.org package is verified during both the
DMG build and first-run setup.

## Acceleration policy

- Whisper alignment uses PyTorch MPS (Apple Metal) when available.
- Demucs uses CPU on macOS for the initial release because its complex-number
  operations still have wider compatibility variance on MPS.
- CPU remains available in the app as a troubleshooting fallback.

## Public signed build

Set these environment variables before running `build-macos.sh`:

- `APPLE_SIGN_IDENTITY`: Developer ID Application identity
- `APPLE_ID`: notarization Apple ID
- `APPLE_TEAM_ID`: Apple Developer team ID
- `APPLE_APP_PASSWORD`: app-specific password

The build downloads the pinned Python.org 3.12 universal2 package for inclusion
in the app. Set `RESOLVE_PYTHON_PKG` to an already downloaded copy when building
offline; the build still verifies its fixed SHA-256 checksum and package
signature.

The script signs the app and DMG, submits the DMG to Apple notarization, and
staples the result. Without these variables it creates an ad-hoc signed beta
for local testing only.

## Remove the development installation

Quit Vilm Lyrics Aligner and DaVinci Resolve, then run:

```bash
chmod +x installer/macos/uninstall-macos.sh
./installer/macos/uninstall-macos.sh
```

This removes the app data, private Python/PyTorch environment, models, app
bundle, and optional Resolve integration. It intentionally leaves Python.org
3.12 installed because other Resolve scripts may depend on the shared runtime.
