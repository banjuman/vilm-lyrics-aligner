from __future__ import annotations

import wave
from pathlib import Path


def wav_duration(path: str | Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / float(audio.getframerate())


def ensure_wav(
    input_path: str | Path,
    output_path: str | Path,
    *,
    sample_rate: int = 48000,
) -> Path:
    """Return WAV input as-is or decode another container to stereo PCM WAV."""
    input_path = Path(input_path).resolve()
    if input_path.suffix.casefold() == ".wav":
        return input_path
    try:
        import av
        import soundfile
    except ImportError as exc:
        raise RuntimeError("PyAV and soundfile are required to decode Resolve audio") from exc

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wrote_audio = False
    with av.open(str(input_path)) as container:
        if not container.streams.audio:
            raise ValueError(f"No audio stream found in {input_path}")
        audio_stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="fltp", layout="stereo", rate=sample_rate)
        with soundfile.SoundFile(
            str(output_path),
            mode="w",
            samplerate=sample_rate,
            channels=2,
            subtype="PCM_24",
        ) as destination:
            for frame in container.decode(audio_stream):
                for converted in resampler.resample(frame):
                    destination.write(converted.to_ndarray().T)
                    wrote_audio = True
            for converted in resampler.resample(None):
                destination.write(converted.to_ndarray().T)
                wrote_audio = True
    if not wrote_audio:
        raise ValueError(f"No decodable audio frames found in {input_path}")
    return output_path
