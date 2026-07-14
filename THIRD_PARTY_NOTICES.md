# Third-party notices

Vilm Lyrics Aligner installs the following third-party components into a
private per-user runtime. These projects retain their own copyrights and
licenses. The links below are the authoritative source and license locations.

| Component | Purpose | License |
| --- | --- | --- |
| [PyTorch](https://github.com/pytorch/pytorch) | Tensor runtime; CUDA, CPU and Apple Metal backends | BSD-3-Clause |
| [TorchAudio](https://github.com/pytorch/audio) | Audio tensor support used by dependencies | BSD-style license |
| [OpenAI Whisper](https://github.com/openai/whisper) | Multilingual speech comparison model and code | MIT |
| [stable-ts](https://github.com/jianfch/stable-ts) | Stable Whisper timestamps and known-text alignment | MIT |
| [Demucs](https://github.com/facebookresearch/demucs) | Vocal separation | MIT |
| [Silero VAD](https://github.com/snakers4/silero-vad) | Voice activity detection model | MIT |
| [PyAV](https://github.com/PyAV-Org/PyAV) | Media decoding | BSD-3-Clause; bundled FFmpeg libraries retain their own licenses |
| [python-soundfile](https://github.com/bastibe/python-soundfile) | WAV/audio file I/O | BSD-3-Clause |
| [librosa](https://github.com/librosa/librosa) | Audio loading and analysis | ISC |
| [lameenc](https://github.com/chrisstaite/lameenc) | Demucs audio dependency | LGPL-3.0-or-later |
| [uv](https://github.com/astral-sh/uv) | Verified private Python/runtime installation | MIT OR Apache-2.0 |
| [CPython](https://www.python.org/) | Private AI runtime and optional shared Resolve scripting runtime | Python Software Foundation License Version 2 |
| [Avalonia](https://github.com/AvaloniaUI/Avalonia) | Native cross-platform desktop interface | MIT |

Additional transitive Python packages are installed from their original PyPI
distributions and remain subject to the license metadata and license files
included by their maintainers. Vilm Lyrics Aligner does not claim ownership of
third-party code, model weights, or trademarks.

The application downloads unmodified runtime packages and model files from
their upstream distribution locations during setup. No supplied lyric text,
audio, or generated subtitle is uploaded by Vilm Lyrics Aligner.
