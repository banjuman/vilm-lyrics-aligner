from __future__ import annotations

import sys
from functools import wraps
from pathlib import Path

from ..device import choose_devices


def _suppress_progress_when_redirected(
    demucs_separate, *, interactive: bool | None = None
) -> None:
    """Hide Demucs' terminal progress bar when output is captured by a GUI."""
    if interactive is None:
        interactive = sys.stderr.isatty()
    if interactive:
        return

    apply_model = demucs_separate.apply_model
    if getattr(apply_model, "_lyrics_aligner_silent_progress", False):
        return

    @wraps(apply_model)
    def apply_model_without_progress(*args, **kwargs):
        kwargs["progress"] = False
        return apply_model(*args, **kwargs)

    setattr(apply_model_without_progress, "_lyrics_aligner_silent_progress", True)
    demucs_separate.apply_model = apply_model_without_progress


def _install_soundfile_io() -> None:
    """Keep Demucs WAV I/O independent of TorchCodec/FFmpeg bindings."""
    import soundfile
    import torch
    import demucs.separate as demucs_separate
    from demucs.audio import convert_audio, prevent_clip

    def load_track(track, audio_channels, samplerate):
        samples, source_rate = soundfile.read(
            str(track), dtype="float32", always_2d=True
        )
        wav = torch.from_numpy(samples.T.copy())
        return convert_audio(wav, source_rate, samplerate, audio_channels)

    def save_audio(
        wav,
        path,
        samplerate,
        bitrate=320,
        clip="rescale",
        bits_per_sample=16,
        as_float=False,
        preset=2,
    ):
        del bitrate, preset
        path = Path(path)
        if path.suffix.casefold() != ".wav":
            raise ValueError("Lyrics Aligner's Demucs backend writes WAV only")
        wav = prevent_clip(wav, mode=clip).detach().cpu().numpy().T
        subtype = "FLOAT" if as_float else f"PCM_{bits_per_sample}"
        soundfile.write(str(path), wav, samplerate, subtype=subtype)

    demucs_separate.load_track = load_track
    demucs_separate.save_audio = save_audio
    _suppress_progress_when_redirected(demucs_separate)


def separate_vocals(
    audio_path: str | Path,
    output_dir: str | Path,
    model: str = "htdemucs",
    device: str = "auto",
) -> Path:
    try:
        import demucs.separate as demucs_separate
    except ImportError as exc:
        raise RuntimeError(
            "Demucs backend is not installed. Run: pip install -e .[separate]"
        ) from exc

    if device == "auto":
        device = choose_devices().separation
    _install_soundfile_io()
    audio_path = Path(audio_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    demucs_separate.main(
        [
            "--two-stems",
            "vocals",
            "--name",
            model,
            "--device",
            device,
            "--out",
            str(output_dir),
            str(audio_path),
        ]
    )
    expected = output_dir / model / audio_path.stem / "vocals.wav"
    if expected.exists():
        return expected
    matches = list(output_dir.glob("**/vocals.wav"))
    if len(matches) == 1:
        return matches[0]
    raise RuntimeError("Demucs finished but vocals.wav was not found")
