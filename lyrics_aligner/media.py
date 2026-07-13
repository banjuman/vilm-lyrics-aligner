from __future__ import annotations

import math
from pathlib import Path


def media_duration(path: str | Path) -> float:
    path = Path(path)
    if path.suffix.casefold() == ".wav":
        try:
            import soundfile
        except ImportError as exc:
            raise RuntimeError("soundfile is required to inspect WAV files") from exc
        info = soundfile.info(str(path))
        if info.samplerate <= 0:
            raise ValueError(f"Could not determine media duration: {path}")
        return info.frames / float(info.samplerate)
    try:
        import av
    except ImportError as exc:
        raise RuntimeError("PyAV is required to inspect media files") from exc
    with av.open(str(path)) as container:
        if not container.streams.audio:
            raise ValueError(f"No audio stream found in {path}")
        stream = container.streams.audio[0]
        if stream.duration is not None and stream.time_base is not None:
            return float(stream.duration * stream.time_base)
        if container.duration is not None:
            return float(container.duration / av.time_base)
    raise ValueError(f"Could not determine media duration: {path}")


def waveform_peaks(path: str | Path, bins: int = 720) -> tuple[float, list[float]]:
    """Return normalized mono peaks without retaining decoded media in memory."""
    if bins < 8:
        raise ValueError("bins must be at least 8")
    try:
        import av
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("PyAV and NumPy are required to draw waveforms") from exc

    path = Path(path)
    duration = media_duration(path)
    if duration <= 0:
        raise ValueError("Media duration must be positive")
    sample_rate = 8000
    total_samples = max(1, int(math.ceil(duration * sample_rate)))
    peaks = np.zeros(bins, dtype=np.float32)
    sample_cursor = 0

    with av.open(str(path)) as container:
        if not container.streams.audio:
            raise ValueError(f"No audio stream found in {path}")
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=sample_rate)

        def consume(frame) -> None:
            nonlocal sample_cursor
            values = np.abs(frame.to_ndarray().reshape(-1)).astype(np.float32, copy=False)
            if not len(values):
                return
            positions = np.arange(sample_cursor, sample_cursor + len(values), dtype=np.int64)
            indices = np.minimum(bins - 1, positions * bins // total_samples)
            np.maximum.at(peaks, indices, values)
            sample_cursor += len(values)

        for decoded in container.decode(stream):
            for converted in resampler.resample(decoded):
                consume(converted)
        for converted in resampler.resample(None):
            consume(converted)

    scale = float(np.percentile(peaks, 98)) if np.any(peaks) else 0.0
    if scale > 0:
        peaks = np.clip(peaks / scale, 0.0, 1.0)
    return duration, [float(value) for value in peaks]


def extract_audio_range(
    input_path: str | Path,
    output_path: str | Path,
    start_seconds: float,
    end_seconds: float | None,
    *,
    sample_rate: int = 48000,
) -> Path:
    """Decode only the requested media interval to stereo PCM WAV."""
    try:
        import av
        import soundfile
    except ImportError as exc:
        raise RuntimeError("PyAV and soundfile are required to extract audio") from exc

    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    duration = media_duration(input_path)
    start = max(0.0, float(start_seconds))
    end = duration if end_seconds is None else min(duration, float(end_seconds))
    if end <= start:
        raise ValueError("The selected range must have a positive duration")

    first_sample = int(round(start * sample_rate))
    last_sample = int(round(end * sample_rate))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cursor = 0
    wrote = 0

    with av.open(str(input_path)) as container:
        if not container.streams.audio:
            raise ValueError(f"No audio stream found in {input_path}")
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="fltp", layout="stereo", rate=sample_rate)
        with soundfile.SoundFile(
            str(output_path),
            mode="w",
            samplerate=sample_rate,
            channels=2,
            subtype="PCM_24",
        ) as destination:
            def consume(frame) -> bool:
                nonlocal cursor, wrote
                samples = frame.to_ndarray().T
                frame_start = cursor
                frame_end = cursor + len(samples)
                cursor = frame_end
                if frame_end <= first_sample:
                    return True
                if frame_start >= last_sample:
                    return False
                left = max(0, first_sample - frame_start)
                right = min(len(samples), last_sample - frame_start)
                if right > left:
                    destination.write(samples[left:right])
                    wrote += right - left
                return frame_end < last_sample

            keep_going = True
            for decoded in container.decode(stream):
                for converted in resampler.resample(decoded):
                    keep_going = consume(converted)
                    if not keep_going:
                        break
                if not keep_going:
                    break
            if keep_going:
                for converted in resampler.resample(None):
                    if not consume(converted):
                        break

    if wrote <= 0:
        output_path.unlink(missing_ok=True)
        raise ValueError("No decodable audio was found in the selected range")
    return output_path
