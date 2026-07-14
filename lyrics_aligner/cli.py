

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .media import waveform_peaks
from .pipeline import align_to_srt, demo_to_srt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lyrics-aligner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    waveform = subparsers.add_parser("waveform")
    waveform.add_argument("media", type=Path)
    waveform.add_argument("--bins", type=int, default=850)

    for name in ("align", "demo"):
        command = subparsers.add_parser(name)
        command.add_argument("audio", type=Path)
        command.add_argument("lyrics", type=Path)
        command.add_argument("-o", "--output", type=Path, required=True)
        command.add_argument("--max-chars", type=int, default=30)

    align = subparsers.choices["align"]
    align.add_argument("--auto-segment", action="store_true")
    align.add_argument(
        "--language",
        default="auto",
        help="dominant spoken language code/name, or 'auto' (default)",
    )
    align.add_argument("--model", default="small")
    align.add_argument("--no-separate", action="store_true")
    align.add_argument(
        "--partial-range",
        action="store_true",
        help="locate and align only the lyric span heard in this audio range",
    )
    align.add_argument("--lead-ms", type=int, default=0)
    align.add_argument("--offset-seconds", type=float, default=0.0)
    align.add_argument("--range-start", type=float, default=0.0)
    align.add_argument("--range-end", type=float)
    align.add_argument("--timeline-anchor", action="store_true")
    align.add_argument("--end-pad-ms", type=int, default=500)
    align.add_argument("--min-duration-ms", type=int, default=500)
    align.add_argument("--max-duration-ms", type=int, default=10000)
    align.add_argument("--min-gap-ms", type=int, default=80)
    align.add_argument("--debug-json", type=Path)
    align.add_argument(
        "--work-dir",
        type=Path,
        help="caller-owned temporary directory (removed by the caller)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "waveform":
            duration, peaks = waveform_peaks(args.media, bins=args.bins)
            print(json.dumps({"duration": duration, "peaks": peaks}, separators=(",", ":")))
            return 0
        lyrics_text = args.lyrics.read_text(encoding="utf-8-sig")
        messages: list[str] = []
        if args.command == "demo":
            cues = demo_to_srt(
                args.audio,
                lyrics_text,
                args.output,
                max_chars=args.max_chars,
            )
        else:
            cues = align_to_srt(
                args.audio,
                lyrics_text,
                args.output,
                max_chars=args.max_chars,
                auto_segment=args.auto_segment,
                language=args.language,
                separate=not args.no_separate,
                partial_range=args.partial_range,
                model_name=args.model,
                lead_ms=args.lead_ms,
                offset_seconds=args.offset_seconds,
                range_start_seconds=args.range_start,
                range_end_seconds=args.range_end,
                timeline_anchor=args.timeline_anchor,
                end_pad_ms=args.end_pad_ms,
                min_duration_ms=args.min_duration_ms,
                max_duration_ms=args.max_duration_ms,
                min_gap_ms=args.min_gap_ms,
                debug_json=args.debug_json,
                messages=messages,
                progress=lambda message: print(message, flush=True),
                work_dir=args.work_dir,
            )
            for message in messages:
                print(f"주의: {message}")
    except Exception as exc:
        print(f"lyrics-aligner: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {len(cues)} cues to {args.output}")
    return 0
