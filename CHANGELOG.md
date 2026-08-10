# Changelog

## 1.0.1 - 2026-08-10

This is a Windows installer compatibility and reliability update. Subtitle
alignment behavior and model choices are unchanged.

- Updated the Windows NVIDIA runtime to the official PyTorch CUDA 12.8 build
  for current GPUs, including RTX 50 series support.
- Added a real CUDA tensor probe. Setup now falls back to the CPU runtime when
  the detected NVIDIA configuration cannot execute the installed CUDA build.
- Added bounded retries for runtime, dependency, and model downloads so users
  have time to approve firewall prompts or recover from temporary network
  interruptions.
- Preserved verified installer downloads after a failed or cancelled setup and
  removed them after a successful installation.
- Improved cancellation so active Python, uv, FFmpeg, and model preparation
  processes are terminated with their child processes.
- Fixed Windows uninstaller self-cleanup so the uninstall directory is removed
  after the product files, Resolve panel, shortcuts, and registry entry.

## 1.0.0 - 2026-07-15

- Initial public release for Windows and Apple silicon macOS.
