from __future__ import annotations

from pathlib import Path
from typing import Sequence

from ..device import choose_devices
from ..languages import whisper_language_code
from ..lyrics import map_units_to_cues
from ..matching import CueTranscriptMatch
from ..models import AlignmentUnit, Cue


def _make_mps_safe_dtw(original_dtw, dtw_cpu):
    """Move MPS costs to CPU before Whisper requests float64 precision."""
    if getattr(original_dtw, "_vilm_mps_safe", False):
        return original_dtw

    def dtw(costs):
        device = getattr(costs, "device", None)
        if getattr(device, "type", None) == "mps":
            return dtw_cpu(costs.cpu().double().numpy())
        return original_dtw(costs)

    dtw._vilm_mps_safe = True
    return dtw


def _install_mps_dtw_compatibility(stable_whisper) -> None:
    """Patch the upstream MPS ordering bug in Whisper word timestamps."""
    import whisper.timing as whisper_timing

    stable_timing = stable_whisper.timing
    safe_dtw = _make_mps_safe_dtw(whisper_timing.dtw, whisper_timing.dtw_cpu)
    whisper_timing.dtw = safe_dtw
    stable_timing.dtw = safe_dtw


class StableWhisperAligner:
    def __init__(
        self,
        model_name: str = "small",
        device: str = "auto",
        download_root: str | Path | None = None,
    ) -> None:
        try:
            import stable_whisper
        except ImportError as exc:
            raise RuntimeError(
                "Whisper alignment backend is not installed. Run: pip install -e .[align]"
            ) from exc

        choice = choose_devices()
        self.device = choice.whisper if device == "auto" else device
        self.device_reason = choice.reason if device == "auto" else f"explicit device: {device}"
        self.last_local_units: dict[int, list[AlignmentUnit]] = {}
        self.last_detected_language: str | None = None
        kwargs = {"device": self.device}
        if self.device == "mps":
            _install_mps_dtw_compatibility(stable_whisper)
        if download_root is not None:
            kwargs["download_root"] = str(Path(download_root))
        self._model = stable_whisper.load_model(model_name, **kwargs)

    def _load_audio(self, audio_path: str | Path):
        try:
            import librosa
        except ImportError as exc:
            raise RuntimeError("librosa is required by the Whisper alignment backend") from exc
        audio, _ = librosa.load(str(Path(audio_path)), sr=16000, mono=True)
        return audio

    def transcribe(
        self, audio_path: str | Path, language: str
    ) -> list[AlignmentUnit]:
        audio = self._load_audio(audio_path)
        language_code = whisper_language_code(language)
        result = self._model.transcribe(
            audio,
            language=language_code,
            vad=True,
            word_timestamps=True,
            regroup=True,
            condition_on_previous_text=False,
            verbose=None,
        )
        self.last_detected_language = getattr(result, "language", None) or language_code
        return _result_units(result)

    def align(self, audio_path: str | Path, text: str, language: str) -> list[AlignmentUnit]:
        audio = self._load_audio(audio_path)
        language_code = whisper_language_code(language) or self.last_detected_language
        line_aware = "\n" in text
        result = self._model.align(
            audio,
            text,
            language=language_code,
            original_split=line_aware,
            fast_mode=not line_aware,
            nonspeech_skip=2.0 if line_aware else 5.0,
            failure_threshold=0.5,
            verbose=None,
        )
        if result is None:
            raise RuntimeError(
                "Whisper alignment failed. The performed lyrics may differ from the supplied text."
            )
        units = _result_units(result)
        if not units:
            raise RuntimeError("Whisper alignment returned no word timestamps")
        return units

    def align_cue_windows(
        self,
        audio_path: str | Path,
        cue_texts: Sequence[str],
        matches: Sequence[CueTranscriptMatch],
        language: str,
        *,
        minimum_similarity: float = 0.62,
        minimum_coverage: float = 0.45,
    ) -> dict[int, Cue]:
        """Re-align selected source lines inside ASR-derived lexical windows.

        Callers may pass conservatively filtered weak matches. Such windows get
        extra room after the observed token so a second word following a long
        sung pause can still be recovered.
        """
        del cue_texts  # Source text is already carried by each match.
        chosen: list[CueTranscriptMatch] = []
        previous_start = -1.0
        for match in matches:
            if (
                match.start is None
                or match.end is None
                or match.similarity < minimum_similarity
                or match.coverage < minimum_coverage
                or match.exact_characters < 2
                or match.start < previous_start
            ):
                continue
            chosen.append(match)
            previous_start = match.start
        self.last_local_units = {}
        if not chosen:
            return {}

        audio = self._load_audio(audio_path)
        duration = len(audio) / 16000
        segments = []
        for index, match in enumerate(chosen):
            is_weak = match.similarity < 0.62 or match.coverage < 0.45
            lower = max(0.0, match.start - (1.2 if is_weak else 0.8))
            upper = min(duration, match.end + (5.0 if is_weak else 1.2))
            if index:
                previous_end = chosen[index - 1].end
                if previous_end is not None:
                    lower = max(lower, previous_end + 0.05)
            if index + 1 < len(chosen):
                next_start = chosen[index + 1].start
                if next_start is not None:
                    upper = min(upper, next_start - 0.10)
            if upper <= lower:
                continue
            segments.append(
                {
                    "start": lower,
                    "end": upper,
                    "text": match.source_text,
                    "match": match,
                }
            )
        _remove_window_overlaps(segments)
        segments = [item for item in segments if item["end"] > item["start"]]
        if not segments:
            return {}

        language_code = whisper_language_code(language) or self.last_detected_language
        align_segments = [
            {"start": item["start"], "end": item["end"], "text": item["text"]}
            for item in segments
        ]
        result = self._model.align_words(audio, align_segments, language_code)
        result_segments = list(getattr(result, "segments", []) or [])
        local_cues: dict[int, Cue] = {}
        if len(result_segments) == len(segments):
            for requested, returned in zip(segments, result_segments):
                match = requested["match"]
                units = _segment_units(returned)
                if not units:
                    continue
                self.last_local_units[match.cue_index] = units
                local_cues[match.cue_index] = Cue(
                    text=match.source_text,
                    start=units[0].start,
                    end=units[-1].end,
                )
            return local_cues

        # Compatibility fallback for stable-ts variants that regroup the
        # supplied windows into a different segment count.
        local_units = _result_units(result)
        mapped = map_units_to_cues(
            [item["match"].source_text for item in segments], local_units
        )
        for requested, cue in zip(segments, mapped):
            match = requested["match"]
            local_cues[match.cue_index] = cue
            self.last_local_units[match.cue_index] = [
                unit
                for unit in local_units
                if unit.end >= cue.start and unit.start <= cue.end
            ]
        return local_cues


def _remove_window_overlaps(segments: list[dict]) -> None:
    """Make ASR-derived alignment windows strictly ascending in place."""
    for current, following in zip(segments, segments[1:]):
        if current["end"] <= following["start"]:
            continue
        current_match = current["match"]
        following_match = following["match"]
        boundary = (float(current_match.end) + float(following_match.start)) / 2
        boundary = max(current["start"] + 0.025, boundary)
        boundary = min(following["end"] - 0.025, boundary)
        current["end"] = boundary - 0.025
        following["start"] = boundary + 0.025


def _segment_units(segment) -> list[AlignmentUnit]:
    units: list[AlignmentUnit] = []
    for word in getattr(segment, "words", None) or []:
        units.append(
            AlignmentUnit(
                text=word.word,
                start=float(word.start),
                end=float(word.end),
            )
        )
    return units


def _result_units(result) -> list[AlignmentUnit]:
    units: list[AlignmentUnit] = []
    if result is None:
        return units
    for segment in result.segments:
        units.extend(_segment_units(segment))
    return units
