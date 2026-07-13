from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from lyrics_aligner.audio import ensure_wav
from lyrics_aligner.backends.demucs import separate_vocals
from lyrics_aligner.device import choose_devices
from lyrics_aligner.timing import VocalActivity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("media", type=Path)
    parser.add_argument("start", type=float)
    parser.add_argument("end", type=float)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="lyrics-aligner-activity-") as temp:
        root = Path(temp)
        wav = ensure_wav(args.media, root / "audio.wav")
        vocals = separate_vocals(
            wav, root / "stems", device=choose_devices().separation
        )
        activity = VocalActivity.from_audio(vocals)
        for start, end in activity.segments(args.start, args.end):
            print(f"{start:.3f}-{end:.3f} duration={end-start:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
