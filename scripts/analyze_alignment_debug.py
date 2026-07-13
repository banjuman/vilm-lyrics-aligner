from __future__ import annotations

import argparse
import json
from pathlib import Path

from lyrics_aligner.cue_mapping import map_units_to_optional_cues
from lyrics_aligner.models import AlignmentUnit


def stamp(cue) -> str:
    if cue is None:
        return "-"
    return f"{cue.start:7.2f}-{cue.end:7.2f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("debug_json", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.debug_json.read_text(encoding="utf-8"))
    matches = payload["transcript_matches"]
    texts = [item["source_text"] for item in matches]
    units = [AlignmentUnit(**item) for item in payload["global_units"]]
    globals_ = map_units_to_optional_cues(texts, units)
    locals_ = payload.get("local_cues", {})

    previous = -1.0
    for index, (match, global_cue) in enumerate(zip(matches, globals_)):
        local = locals_.get(str(index))
        chosen_start = local["start"] if local else (global_cue.start if global_cue else None)
        reversal = chosen_start is not None and chosen_start + 0.01 < previous
        if chosen_start is not None:
            previous = max(previous, chosen_start)
        asr = "-" if match["start"] is None else f"{match['start']:7.2f}-{match['end']:7.2f}"
        local_stamp = "-" if not local else f"{local['start']:7.2f}-{local['end']:7.2f}"
        flag = " REVERSE" if reversal else ""
        print(
            f"{index + 1:02d} {match['status']:<7} "
            f"ASR {asr} G {stamp(global_cue)} L {local_stamp}{flag} | "
            f"{match['source_text']}"
        )

    print("\nFINAL CUES")
    for index, cue in enumerate(payload["cues"], 1):
        print(f"{index:02d} {cue['start']:7.2f}-{cue['end']:7.2f} | {cue['text']}")
    print("\nMESSAGES")
    for message in payload.get("messages", []):
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
