from __future__ import annotations

import re

from .lyrics import normalize_line, split_lyrics
from .matching import normalize_for_match


_HIDDEN_LINE = re.compile(r"^\((.+)\)$")


def split_manual_lyrics_with_hidden(
    text: str, max_chars: int
) -> tuple[list[str], set[int]]:
    """Parse manual lyrics and return standalone parenthetical hidden cues.

    Only a complete line such as ``(음)`` is special. Parentheses embedded in
    a visible lyric remain ordinary caption text. Hidden cue contents are
    aligned like supplied lyrics but removed only after timing has been
    polished, so they reserve an intentional caption-free vocal interval.
    """

    cue_texts: list[str] = []
    hidden_indices: set[int] = set()
    for raw_line in text.splitlines():
        line = normalize_line(raw_line)
        if not line:
            continue
        hidden_match = _HIDDEN_LINE.fullmatch(line)
        if hidden_match:
            inner = normalize_line(hidden_match.group(1))
            if normalize_for_match(inner):
                hidden_indices.add(len(cue_texts))
                cue_texts.append(inner)
                continue
        cue_texts.extend(split_lyrics(line, max_chars=max_chars))
    return cue_texts, hidden_indices
