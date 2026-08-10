# Development log

## 2026-08-01 - v1.0.1 Windows CUDA compatibility hotfix

- Kept the subtitle alignment behavior unchanged.
- Updated the Windows NVIDIA runtime from PyTorch CUDA 12.6 to the official
  CUDA 12.8 build so Blackwell GPUs such as the RTX 5060 (`sm_120`) are
  supported.
- Replaced the `torch.cuda.is_available()`-only installer check with a real
  CUDA tensor operation and synchronization. If that probe fails, setup
  reinstalls the CPU runtime instead of aborting later during model setup.
- Bumped product and package metadata from 1.0.0 to 1.0.1. The published
  1.0.0 tag and artifacts remain immutable.
- Required release validation: CPU install, existing RTX 3060 regression,
  and an RTX 5060 install/run confirmation before replacing the public
  download.
- Local verification completed: 136 Python tests passed, both .NET projects
  built without errors, and the packaged single-file installer passed its
  embedded-payload self-test.

## 2026-08-10 - v1.0.1 Windows installer network resilience

- A public v1.0.0 report showed that a restrictive firewall prompt could make
  the bootstrap installer abort while uv, Python, packages, or models were
  being downloaded.
- Added four bounded attempts for network-dependent subprocesses with 5, 10,
  and 20 second waits. The log explicitly tells the user to approve a pending
  firewall dialog during the wait.
- Added the same bounded retry policy to the pinned uv HTTP download, using a
  partial file and SHA-256 verification before promoting it into the cache.
- Failed or cancelled installs retain the verified install cache so a new
  setup run can reuse downloads; successful installs still remove the cache.
- Cancellation now terminates the active child process tree instead of leaving
  Python, uv, FFmpeg, or model preparation running after setup closes.
- Alignment behavior and model choices were not changed.
- Local verification completed: 137 Python tests passed, the Windows desktop
  and setup projects built successfully, and the rebuilt single-file setup
  passed its embedded payload self-test.
- Remote E2E candidate SHA-256 after installer cleanup fixes:
  `EC7F277C057548E59B0EB5DCE45E22430426AC22BC51E3A34996C18A88283BAD`.
- The same candidate was copied to a clean Windows 11 AMD test machine; its
  remote hash and self-test matched. A clean GUI install completed successfully
  using the intended CPU fallback.
- Remote post-install checks passed: app `1.0.1`, PyTorch `2.11.0+cpu`, CLI exit
  0, Desktop/Start Menu/Resolve panel present, Windows uninstall entry present,
  install cache removed, and the Desktop process remained healthy after a
  six-second launch probe.
- The first uninstall E2E exposed a quoting bug in the delayed self-cleanup
  command: only `C:\ProgramData\LyricsAligner\uninstall.ps1` remained. The
  cleanup command now uses PowerShell `-EncodedCommand`; a second remote E2E
  removed the app, models, panel, shortcut, registry key, and uninstall folder.
- A deterministic retry E2E interrupted only the first managed `uv.exe`
  process. Setup started a new `uv.exe` after the configured delay and
  completed Python, packages, models, CPU backend config, Resolve integration,
  and success-only cache cleanup. No test firewall rules remained.
- The public release EXE was rebuilt from the same installer source, passed its
  embedded-payload self-test, and has SHA-256
  `11D21B82B3E53EECF6026D73FAA8E033CB4B858C832ED9C52099EC21C15A025A`.
