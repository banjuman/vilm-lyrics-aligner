from __future__ import annotations

import argparse
import time
from pathlib import Path

import soundfile

from lyrics_aligner.backends.stable_whisper import StableWhisperAligner


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--vad", action="store_true")
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()

    samples, sample_rate = soundfile.read(
        args.source, dtype="float32", always_2d=True
    )
    samples = samples[: round(sample_rate * args.seconds)]
    short_path = Path(__file__).resolve().parents[1] / "whisper-short-profile.wav"
    soundfile.write(short_path, samples, sample_rate, subtype="FLOAT")

    started = time.monotonic()
    aligner = StableWhisperAligner(model_name="small", device=args.device)
    print(f"device={args.device} model_load={time.monotonic() - started:.2f}s", flush=True)
    audio = aligner._load_audio(short_path)
    transcribe_started = time.monotonic()
    result = aligner._model.transcribe(
        audio,
        language="ko",
        vad=args.vad,
        word_timestamps=True,
        regroup=True,
        condition_on_previous_text=False,
        verbose=None,
    )
    words = sum(len(segment.words or []) for segment in result.segments)
    print(
        f"vad={args.vad} transcribe={time.monotonic() - transcribe_started:.2f}s words={words}",
        flush=True,
    )
    short_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
