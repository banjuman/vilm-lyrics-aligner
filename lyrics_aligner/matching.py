from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Sequence

from .models import AlignmentUnit


@dataclass(frozen=True)
class CueTranscriptMatch:
    cue_index: int
    source_text: str
    transcript_text: str
    start: float | None
    end: float | None
    similarity: float
    coverage: float
    exact_characters: int
    status: str

    @property
    def usable_anchor(self) -> bool:
        return (
            self.start is not None
            and self.end is not None
            and self.exact_characters >= 2
            and self.similarity >= 0.48
            and self.coverage >= 0.45
        )


@dataclass(frozen=True)
class _ObservedCharacter:
    value: str
    start: float
    end: float
    unit_index: int


def normalize_for_match(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(character for character in normalized if character.isalnum())


def compare_lyrics_to_transcript(
    cue_texts: Sequence[str],
    transcript_units: Sequence[AlignmentUnit],
) -> list[CueTranscriptMatch]:
    """Monotonically compare supplied cue text with timestamped ASR output."""
    source_characters: list[str] = []
    source_cues: list[int] = []
    cue_keys: list[str] = []
    for cue_index, text in enumerate(cue_texts):
        key = normalize_for_match(text)
        cue_keys.append(key)
        source_characters.extend(key)
        source_cues.extend([cue_index] * len(key))

    observed, unit_keys = _expand_transcript(transcript_units)
    if not source_characters or not observed:
        return [
            CueTranscriptMatch(
                cue_index=index,
                source_text=text,
                transcript_text="",
                start=None,
                end=None,
                similarity=0.0,
                coverage=0.0,
                exact_characters=0,
                status="missing",
            )
            for index, text in enumerate(cue_texts)
        ]

    mapping = _align_characters(source_characters, [item.value for item in observed])
    matches: list[CueTranscriptMatch] = []
    for cue_index, (source_text, source_key) in enumerate(zip(cue_texts, cue_keys)):
        source_indices = [
            index for index, owner in enumerate(source_cues) if owner == cue_index
        ]
        mapped = [mapping[index] for index in source_indices if mapping[index] is not None]
        observed_indices = [int(index) for index in mapped]
        exact = sum(
            source_characters[source_index] == observed[int(mapping[source_index])].value
            for source_index in source_indices
            if mapping[source_index] is not None
        )
        coverage = len(observed_indices) / len(source_indices) if source_indices else 0.0

        if observed_indices:
            first_character = min(observed_indices)
            last_character = max(observed_indices)
            first_unit = observed[first_character].unit_index
            last_unit = observed[last_character].unit_index
            transcript_key = "".join(unit_keys[first_unit : last_unit + 1])
            transcript_text = " ".join(
                transcript_units[index].text.strip()
                for index in range(first_unit, last_unit + 1)
                if transcript_units[index].text.strip()
            )
            start = observed[first_character].start
            end = observed[last_character].end
            similarity = SequenceMatcher(None, source_key, transcript_key).ratio()
        else:
            transcript_text = ""
            start = None
            end = None
            similarity = 0.0

        if similarity >= 0.84 and coverage >= 0.75:
            status = "match"
        elif similarity >= 0.48 and coverage >= 0.45:
            status = "changed"
        else:
            status = "weak"
        matches.append(
            CueTranscriptMatch(
                cue_index=cue_index,
                source_text=source_text,
                transcript_text=transcript_text,
                start=start,
                end=end,
                similarity=similarity,
                coverage=coverage,
                exact_characters=exact,
                status=status,
            )
        )
    return matches


def _expand_transcript(
    units: Sequence[AlignmentUnit],
) -> tuple[list[_ObservedCharacter], list[str]]:
    observed: list[_ObservedCharacter] = []
    unit_keys: list[str] = []
    for unit_index, unit in enumerate(units):
        key = normalize_for_match(unit.text)
        unit_keys.append(key)
        if not key:
            continue
        duration = max(0.0, unit.end - unit.start)
        for character_index, character in enumerate(key):
            start = unit.start + duration * character_index / len(key)
            end = unit.start + duration * (character_index + 1) / len(key)
            observed.append(_ObservedCharacter(character, start, end, unit_index))
    return observed, unit_keys


def _align_characters(source: Sequence[str], observed: Sequence[str]) -> list[int | None]:
    """Semi-global Needleman-Wunsch alignment with free ASR prefix/suffix."""
    match_score = 3
    mismatch_score = -2
    gap_score = -2
    width = len(observed) + 1
    trace = [bytearray(width) for _ in range(len(source) + 1)]
    previous = [0] * width  # leading transcript/ad-lib characters are free

    for source_index in range(1, len(source) + 1):
        current = [source_index * gap_score] + [0] * len(observed)
        trace[source_index][0] = 1
        for observed_index in range(1, width):
            diagonal = previous[observed_index - 1] + (
                match_score
                if source[source_index - 1] == observed[observed_index - 1]
                else mismatch_score
            )
            up = previous[observed_index] + gap_score
            left = current[observed_index - 1] + gap_score
            best = max(diagonal, up, left)
            current[observed_index] = best
            trace[source_index][observed_index] = 0 if diagonal == best else (1 if up == best else 2)
        previous = current

    observed_index = max(range(width), key=previous.__getitem__)
    source_index = len(source)
    mapping: list[int | None] = [None] * len(source)
    while source_index > 0:
        direction = trace[source_index][observed_index]
        if direction == 0 and observed_index > 0:
            mapping[source_index - 1] = observed_index - 1
            source_index -= 1
            observed_index -= 1
        elif direction == 1 or observed_index == 0:
            source_index -= 1
        else:
            observed_index -= 1
    return mapping
