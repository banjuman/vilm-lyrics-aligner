from __future__ import annotations

from collections.abc import Sequence

from .models import Cue


def format_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def render_srt(
    cues: Sequence[Cue],
    offset_seconds: float = 0.0,
    *,
    timeline_anchor: bool = False,
) -> str:
    blocks: list[str] = []
    first_cue_index = 1
    if timeline_anchor and cues:
        earliest_start = min(cue.start + offset_seconds for cue in cues)
        if earliest_start > 0.6:
            # Resolve positions imported SRT clips relative to their first cue.
            # U+2800 looks blank but is a real symbol, so Resolve keeps the cue.
            anchor_end = min(0.5, earliest_start)
            blocks.append(
                "1\n"
                f"00:00:00,000 --> {format_timestamp(anchor_end)}\n"
                "\u2800"
            )
            first_cue_index = 2
    for index, cue in enumerate(cues, start=first_cue_index):
        start = format_timestamp(cue.start + offset_seconds)
        end = format_timestamp(cue.end + offset_seconds)
        blocks.append(f"{index}\n{start} --> {end}\n{cue.text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")
