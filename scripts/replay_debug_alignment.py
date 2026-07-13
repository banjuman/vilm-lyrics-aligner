from __future__ import annotations

import argparse
import json
from pathlib import Path

from lyrics_aligner.pipeline import align_to_srt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("debug_json", type=Path)
    parser.add_argument("output_srt", type=Path)
    args = parser.parse_args()

    previous = json.loads(args.debug_json.read_text(encoding="utf-8"))
    lyrics = "\n".join(
        item["source_text"] for item in previous["transcript_matches"]
    )
    output_debug = args.output_srt.with_suffix(".json")
    messages: list[str] = []
    cues = align_to_srt(
        args.audio,
        lyrics,
        args.output_srt,
        auto_segment=True,
        max_chars=30,
        max_duration_ms=10000,
        min_gap_ms=80,
        debug_json=output_debug,
        messages=messages,
    )
    print(f"cues={len(cues)} debug={output_debug}")
    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
