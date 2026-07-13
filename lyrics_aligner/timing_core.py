

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .models import Cue


@dataclass(frozen=True)
class VocalActivity:
    """Compact vocal-activity mask used for cue-boundary correction."""

    active: tuple[bool, ...]
    hop_seconds: float

    @property
    def duration(self) -> float:
        return len(self.active) * self.hop_seconds

    @classmethod
    def from_audio(cls, path: str | Path, *, hop_seconds: float = 0.01) -> "VocalActivity":
        import librosa
        import numpy as np

        sample_rate = 16000
        audio, _ = librosa.load(str(Path(path)), sr=sample_rate, mono=True)
        hop_length = max(1, round(sample_rate * hop_seconds))
        frame_length = max(hop_length * 2, round(sample_rate * 0.04))
        rms = librosa.feature.rms(
            y=audio, frame_length=frame_length, hop_length=hop_length, center=True
        )[0]
        if not len(rms) or float(np.max(rms)) <= 1e-8:
            return cls(tuple(False for _ in rms), hop_seconds)

        db = librosa.amplitude_to_db(rms, ref=np.max)
        floor = float(np.percentile(db, 20))
        high = float(np.percentile(db, 90))
        threshold = max(-42.0, floor + max(6.0, (high - floor) * 0.35))
        mask = [bool(value >= threshold) for value in db]
        mask = _fill_short_gaps(mask, round(0.12 / hop_seconds))
        mask = _remove_short_runs(mask, round(0.08 / hop_seconds))
        return cls(tuple(mask), hop_seconds)

    @classmethod
    def from_segments(
        cls,
        duration: float,
        segments: Iterable[tuple[float, float]],
        *,
        hop_seconds: float = 0.01,
    ) -> "VocalActivity":
        size = max(1, int(duration / hop_seconds) + 1)
        mask = [False] * size
        for start, end in segments:
            first = max(0, int(start / hop_seconds))
            last = min(size, int(end / hop_seconds) + 1)
            for index in range(first, last):
                mask[index] = True
        return cls(tuple(mask), hop_seconds)

    def snap_start(
        self,
        predicted: float,
        *,
        search_before: float = 0.25,
        search_after: float = 0.30,
    ) -> float:
        # Inspect beyond the search window so a vocal held from the previous
        # line is not mistaken for a new onset at the left window boundary.
        segments = self.segments(
            max(0.0, predicted - search_before - 1.0), predicted + search_after
        )
        onsets = [
            start
            for start, _ in segments
            if predicted - search_before <= start <= predicted + search_after
        ]
        if not onsets:
            return predicted
        return min(onsets, key=lambda start: abs(start - predicted))

    def tail_end(
        self,
        predicted: float,
        *,
        search_before: float = 0.2,
        search_after: float = 4.0,
    ) -> float:
        segments = self.segments(
            max(0.0, predicted - search_before - 1.0), predicted + search_after
        )
        nearby = [
            item
            for item in segments
            if item[0] <= predicted + 0.25 and item[1] >= predicted - search_before
        ]
        if not nearby:
            return predicted
        return max(predicted, nearby[-1][1])

    def phrase_end(
        self,
        start: float,
        *,
        max_search: float = 12.0,
        bridge_silence: float = 0.8,
    ) -> float:
        """Find the end of the active phrase after start, bridging short breaths."""
        segments = self.segments(max(0.0, start - 1.0), start + max_search)
        candidates = [item for item in segments if item[1] >= start - 0.1]
        if not candidates:
            return start
        _, current_end = candidates[0]
        for next_start, next_end in candidates[1:]:
            if next_start - current_end > bridge_silence:
                break
            current_end = next_end
        return max(start, current_end)

    def segments(self, start: float = 0.0, end: float | None = None) -> list[tuple[float, float]]:
        if end is None:
            end = self.duration
        first = max(0, int(start / self.hop_seconds))
        last = min(len(self.active), int(end / self.hop_seconds) + 1)
        result: list[tuple[float, float]] = []
        run_start: int | None = None
        for index in range(first, last):
            if self.active[index] and run_start is None:
                run_start = index
            elif not self.active[index] and run_start is not None:
                result.append((run_start * self.hop_seconds, index * self.hop_seconds))
                run_start = None
        if run_start is not None:
            result.append((run_start * self.hop_seconds, last * self.hop_seconds))
        return result


def polish_singing_cue_times(
    cues: Sequence[Cue],
    *,
    activity: VocalActivity | None = None,
    lead_ms: int = 0,
    end_hold_ms: int = 500,
    min_duration_ms: int = 500,
    max_duration_ms: int = 10000,
    min_gap_ms: int = 80,
) -> list[Cue]:
    """Apply singing-aware start, vocal-tail, hold, and soft-duration rules."""
    if not cues:
        return []
    lead = max(0, lead_ms) / 1000
    hold = max(0, end_hold_ms) / 1000
    minimum = max(0, min_duration_ms) / 1000
    maximum = max(0, max_duration_ms) / 1000
    requested_gap = max(0, min_gap_ms) / 1000

    acoustic_starts: list[float] = []
    for cue in cues:
        detected = activity.snap_start(cue.start) if activity else cue.start
        # Vocal activity may contain a breath, hum, or the previous sustained
        # vowel. Never let it undo a lexical start guard by moving earlier.
        acoustic_starts.append(max(0.0, cue.start, detected))

    display_starts: list[float] = []
    for index, acoustic_start in enumerate(acoustic_starts):
        display_start = max(0.0, acoustic_start - lead)
        if index:
            previous = cues[index - 1]
            previous_duration = previous.end - previous.start
            if not maximum or previous_duration <= maximum:
                # The next lyric may lead its own onset, but never at the cost
                # of cutting a trusted previous syllable. Do not add the visual
                # gap here: it is inserted only when real acoustic room exists.
                display_start = max(display_start, previous.end)
        display_starts.append(display_start)

    result: list[Cue] = []
    for index, cue in enumerate(cues):
        start = display_starts[index]
        raw_duration = max(0.0, cue.end - cue.start)
        vocal_end = cue.end
        if activity:
            if maximum and raw_duration > maximum:
                vocal_end = activity.phrase_end(
                    acoustic_starts[index], max_search=maximum + 2.0
                )
            else:
                vocal_end = activity.tail_end(cue.end)

        trusted_raw_end = cue.end if not maximum or raw_duration <= maximum else start
        desired_end = max(trusted_raw_end, vocal_end) + hold
        if maximum:
            cap = start + maximum
            desired_end = max(vocal_end, min(desired_end, cap))

        boundary = None
        if index + 1 < len(cues):
            next_start = display_starts[index + 1]
            # A small blank transition is useful only when it fits after the
            # trusted sung tail. Otherwise switch directly without cutting the
            # previous lyric or delaying the next lyric.
            transition_gap = (
                requested_gap
                if next_start - trusted_raw_end >= requested_gap
                else 0.0
            )
            boundary = max(start, next_start - transition_gap)
            desired_end = min(desired_end, boundary)

        end = max(desired_end, start + minimum)
        if boundary is not None:
            end = min(end, boundary)
        result.append(Cue(text=cue.text, start=start, end=max(start, end)))
    return result


def _fill_short_gaps(mask: list[bool], maximum: int) -> list[bool]:
    result = mask[:]
    index = 0
    while index < len(result):
        if result[index]:
            index += 1
            continue
        start = index
        while index < len(result) and not result[index]:
            index += 1
        if start > 0 and index < len(result) and index - start <= maximum:
            result[start:index] = [True] * (index - start)
    return result


def _remove_short_runs(mask: list[bool], minimum: int) -> list[bool]:
    result = mask[:]
    index = 0
    while index < len(result):
        if not result[index]:
            index += 1
            continue
        start = index
        while index < len(result) and result[index]:
            index += 1
        if index - start < minimum:
            result[start:index] = [False] * (index - start)
    return result
