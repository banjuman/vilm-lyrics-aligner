# Apple silicon macOS validation

Target for the first validation: M1 Pro, 16 GB RAM, macOS 14 or later, DaVinci
Resolve Studio.

## 1. Build and first launch

```bash
xcode-select --install
chmod +x installer/macos/*.sh
./installer/macos/build-macos.sh
```

Open the DMG, drag the app to Applications, then Control-click the ad-hoc signed
development app and choose **Open**. The first-run screen should:

- explain the private runtime and expected disk use;
- detect Resolve Studio and preselect its optional integration;
- finish without opening Terminal;
- explain that Resolve integration installs the shared Python.org 3.12 runtime
  when it is not already present;
- request one administrator approval for the shared Resolve Python runtime and
  panel;
- keep the setup window open while every selected component is installed and
  verified;
- show **Open Vilm Lyrics Aligner** only after setup completes, then open the
  normal window when the user selects it.

On a clean Mac, confirm setup creates
`/Library/Frameworks/Python.framework/Versions/3.12/Python`. Repeat setup and
confirm it reuses the existing framework rather than reinstalling it.

Check the saved backend:

```bash
cat "$HOME/Library/Application Support/Vilm Lyrics Aligner/config.json"
```

The backend should be `mps`. The app's processing-device list should show
**Apple GPU · Metal** and **CPU**, with Metal selected.

## 2. Standalone behavior

Test a known-good 3–4 minute song previously used on Windows.

1. Generate an SRT for the full file in Auto mode.
2. Generate an SRT for a waveform-selected range and verify that its cues retain
   the original media offset in Resolve.
3. Repeat one short range with CPU selected. It may be slower, but output should
   remain structurally equivalent.
4. Cancel once during vocal separation and once during alignment. The UI should
   return promptly and no Python process should continue consuming CPU.

Compare cue order, missing lines, first-line start, and last-line end with the
same Windows test source. Small floating-point timing differences are expected;
source-text order changes are not.

## 3. Resolve Studio integration

Restart Resolve after first-run setup.

1. Confirm `Workspace > Workflow Integrations > Vilm Lyrics Aligner` opens.
2. Run a full-timeline test and confirm the generated subtitles are added without
   deleting existing subtitle clips.
3. Set a clear In/Out range, paste the full-song lyrics, and run the partial job.
4. Confirm Resolve's original In/Out marks remain after the temporary render.
5. Confirm the first imported subtitle lands inside the selected range rather
   than at timeline start.

## 4. Storage and removal

Temporary media and separated stems should disappear after success, failure, or
cancellation. Durable runtime and model files belong only under:

```text
~/Library/Application Support/Vilm Lyrics Aligner
```

After testing, close Resolve and run:

```bash
./installer/macos/uninstall-macos.sh
```

Confirm that the app, private runtime/models, and Resolve panel are gone while
unrelated project environments remain untouched. Python.org 3.12 should remain
installed because it is a shared Resolve scripting dependency.

## Report back

For a failure, capture:

- the setup or processing log shown in the app;
- the current `config.json` with personal paths redacted if desired;
- macOS and Resolve version;
- whether the failure occurred with Metal, CPU, standalone, or Resolve.
