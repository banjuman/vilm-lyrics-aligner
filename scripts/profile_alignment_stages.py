from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from lyrics_aligner.backends.stable_whisper import StableWhisperAligner
from lyrics_aligner.cue_mapping import map_units_to_optional_cues
from lyrics_aligner.matching import compare_lyrics_to_transcript
from lyrics_aligner.pipeline import _select_window_matches


def report(label: str, started: float) -> float:
    now = time.monotonic()
    print(f"{label}: {now - started:.2f}s", flush=True)
    return now


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vocals", type=Path)
    parser.add_argument("debug_json", type=Path)
    args = parser.parse_args()

    previous = json.loads(args.debug_json.read_text(encoding="utf-8"))
    cue_texts = [item["source_text"] for item in previous["transcript_matches"]]
    started = time.monotonic()
    aligner = StableWhisperAligner(model_name="small", device="cuda")
    checkpoint = report("model_load", started)
    transcript = aligner.transcribe(args.vocals, "Korean")
    checkpoint = report("transcribe", checkpoint)
    matches = compare_lyrics_to_transcript(cue_texts, transcript)
    checkpoint = report("compare", checkpoint)
    global_units = aligner.align(args.vocals, "\n".join(cue_texts), "Korean")
    checkpoint = report("global_align", checkpoint)
    global_cues = map_units_to_optional_cues(cue_texts, global_units)
    selected = _select_window_matches(matches, global_cues)
    checkpoint = report(f"select_{len(selected)}_windows", checkpoint)
    local = aligner.align_cue_windows(
        args.vocals,
        cue_texts,
        selected,
        "Korean",
        minimum_similarity=0.48,
        minimum_coverage=0.33,
    )
    report(f"local_align_{len(local)}", checkpoint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
