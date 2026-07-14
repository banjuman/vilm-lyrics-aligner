from __future__ import annotations

import json
import tempfile
from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Sequence

from .audio import ensure_wav, wav_duration
from .backends.demucs import separate_vocals
from .backends.stable_whisper import StableWhisperAligner
from .cue_mapping import map_units_to_optional_cues
from .device import choose_devices
from .hidden_vocals import HiddenVocalGap, infer_hidden_vocal_gaps
from .lyric_annotations import split_manual_lyrics_with_hidden
from .lyrics import split_lyrics, split_lyrics_with_paragraph_barriers
from .matching import CueTranscriptMatch, compare_lyrics_to_transcript
from .media import extract_audio_range
from .models import AlignmentUnit, Cue
from .segmentation import auto_segment_source_cues, merge_obvious_wrapped_lines
from .srt import render_srt
from .start_verification import StartAdjustment, refine_start_from_evidence
from .timing import VocalActivity, polish_singing_cue_times


_HIDDEN_PREFIX = "[[LYRICS_ALIGNER_HIDDEN]]"


def align_to_srt(
    audio_path: str | Path,
    lyrics_text: str,
    output_path: str | Path,
    *,
    max_chars: int = 30,
    auto_segment: bool = False,
    language: str = "auto",
    separate: bool = True,
    partial_range: bool = False,
    model_name: str = "small",
    lead_ms: int = 0,
    offset_seconds: float = 0.0,
    range_start_seconds: float = 0.0,
    range_end_seconds: float | None = None,
    timeline_anchor: bool = False,
    end_pad_ms: int = 500,
    min_duration_ms: int = 500,
    max_duration_ms: int = 10000,
    min_gap_ms: int = 80,
    debug_json: str | Path | None = None,
    messages: list[str] | None = None,
    progress: Callable[[str], None] | None = None,
    work_dir: str | Path | None = None,
) -> list[Cue]:
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    if not audio_path.is_file():
        raise FileNotFoundError(audio_path)

    alignment_line_limit = 80 if auto_segment else max_chars
    if auto_segment:
        cue_texts, paragraph_barriers = split_lyrics_with_paragraph_barriers(
            lyrics_text, max_chars=alignment_line_limit
        )
        hidden_source_indices: set[int] = set()
    else:
        cue_texts, hidden_source_indices = split_manual_lyrics_with_hidden(
            lyrics_text, max_chars=alignment_line_limit
        )
        paragraph_barriers = set()
    if not cue_texts:
        raise ValueError("Lyrics are empty")
    if len(hidden_source_indices) == len(cue_texts):
        raise ValueError("At least one visible lyric line is required")

    log = messages if messages is not None else []
    report = progress if progress is not None else (lambda _message: None)
    report("Preparing audio…")
    device_choice = choose_devices()
    log.append(f"장치: {device_choice.reason}")
    local_units_by_index: dict[int, list[AlignmentUnit]] = {}
    start_adjustments: list[StartAdjustment] = []
    auto_hidden_gaps: list[HiddenVocalGap] = []
    hidden_timing_cues: list[Cue] = []

    if work_dir is None:
        temporary_context = tempfile.TemporaryDirectory(prefix="lyrics-aligner-")
    else:
        temporary_path = Path(work_dir).resolve()
        temporary_path.mkdir(parents=True, exist_ok=True)
        temporary_context = nullcontext(str(temporary_path))

    with temporary_context as temporary:
        temporary_path = Path(temporary)
        range_start = max(0.0, float(range_start_seconds))
        if range_start > 0.0 or range_end_seconds is not None:
            source_wav = extract_audio_range(
                audio_path,
                temporary_path / "selected-audio.wav",
                range_start,
                range_end_seconds,
            )
            partial_range = True
        else:
            source_wav = ensure_wav(audio_path, temporary_path / "resolve-audio.wav")
        duration = wav_duration(source_wav)
        report(f"Audio duration: {duration:.2f}s")
        align_audio = source_wav
        if separate:
            report("Separating vocals…")
            align_audio = separate_vocals(
                source_wav,
                temporary_path / "stems",
                device=device_choice.separation,
            )

        try:
            activity = VocalActivity.from_audio(align_audio)
        except Exception as exc:
            activity = None
            log.append(f"보컬 경계 분석을 건너뜀: {exc}")

        report("Loading the alignment model and comparing the vocals…")
        aligner = StableWhisperAligner(
            model_name=model_name, device=device_choice.whisper
        )
        transcript_units = aligner.transcribe(align_audio, language)
        detected_language = aligner.last_detected_language
        if language.casefold() == "auto" and detected_language:
            log.append(f"Detected dominant language: {detected_language}")
        transcript_matches = compare_lyrics_to_transcript(cue_texts, transcript_units)
        if partial_range:
            span = _partial_lyric_span(transcript_matches)
            if span is None:
                raise ValueError(
                    "The selected In/Out audio could not be matched to the supplied lyrics"
                )
            first, last = span
            if first != 0 or last != len(cue_texts) - 1:
                log.append(
                    f"In/Out matched original lyric lines {first + 1}-{last + 1}"
                )
                cue_texts = cue_texts[first : last + 1]
                hidden_source_indices = {
                    index - first
                    for index in hidden_source_indices
                    if first <= index <= last
                }
                paragraph_barriers = {
                    index - first
                    for index in paragraph_barriers
                    if first <= index < last
                }
                transcript_matches = compare_lyrics_to_transcript(
                    cue_texts, transcript_units
                )
        if auto_segment:
            auto_hidden_gaps = infer_hidden_vocal_gaps(
                transcript_matches, transcript_units
            )

        # Manual hidden lines are part of cue_texts because the user explicitly
        # supplied their approximate sound. Automatically inferred gaps never
        # alter this full-song alignment text: adding guessed tokens here can
        # disturb later repeated verses after a long instrumental section.
        report("Aligning the full original lyrics…")
        global_units = aligner.align(align_audio, "\n".join(cue_texts), language)
        failed_tail_units = [
            unit
            for unit in global_units
            if unit.start >= duration - 0.25 and unit.end - unit.start <= 0.05
        ]
        if failed_tail_units:
            global_units = [
                unit for unit in global_units if unit not in failed_tail_units
            ]
            log.append(
                f"매체 끝점에 뭉친 정렬 실패 단어 {len(failed_tail_units)}개를 제외함"
            )
        global_cues = map_units_to_optional_cues(cue_texts, global_units)

        report("Refining individual cue boundaries…")
        window_matches = _select_window_matches(transcript_matches, global_cues)
        try:
            local_cues = aligner.align_cue_windows(
                align_audio,
                cue_texts,
                window_matches,
                language,
                minimum_similarity=0.62,
                minimum_coverage=0.45,
            )
            local_units_by_index = aligner.last_local_units
        except Exception as exc:
            local_cues = {}
            local_units_by_index = {}
            log.append(f"ASR 구간 재정렬을 건너뜀: {exc}")

        source_cues: dict[int, Cue] = {}
        unresolved: list[int] = []
        unresolved_hidden: list[int] = []
        for index, text in enumerate(cue_texts):
            cue = local_cues.get(index) or global_cues[index]
            if cue is None:
                (unresolved_hidden if index in hidden_source_indices else unresolved).append(
                    index
                )
                continue
            if index in hidden_source_indices:
                source_cues[index] = Cue(
                    text=_mark_hidden(text), start=cue.start, end=cue.end
                )
                continue
            refined, adjustments = refine_start_from_evidence(
                index,
                cue,
                transcript_matches[index],
                previous_match=(transcript_matches[index - 1] if index else None),
                local_cue=local_cues.get(index),
                global_cue=global_cues[index],
            )
            start_adjustments.extend(adjustments)
            source_cues[index] = Cue(text=text, start=refined.start, end=refined.end)

        if unresolved:
            lines = ", ".join(str(index + 1) for index in unresolved)
            log.append(f"정렬 근거가 없어 제외한 원문 줄: {lines}")
        if unresolved_hidden:
            lines = ", ".join(str(index + 1) for index in unresolved_hidden)
            log.append(f"정렬하지 못한 숨은 보컬 힌트 줄: {lines}")
        if hidden_source_indices:
            log.append(
                f"괄호로 지정한 숨은 보컬 {len(hidden_source_indices)}곳을 "
                "자막 없는 정렬 구간으로 사용함"
            )
        if auto_hidden_gaps:
            log.append(
                f"원문 사이의 짧은 비가사 보컬 {len(auto_hidden_gaps)}곳을 "
                "자동으로 자막 없는 구간으로 사용함"
            )

        lexical_guards = sum(
            adjustment.kind == "lexical_floor" for adjustment in start_adjustments
        )
        sustained_guards = sum(
            adjustment.kind == "sustained_boundary_consensus"
            for adjustment in start_adjustments
        )
        if lexical_guards:
            log.append(
                f"실제 글자 시작보다 이른 정렬 {lexical_guards}곳을 "
                "보수적으로 뒤로 보정함"
            )
        if sustained_guards:
            log.append(
                f"앞 소절 지속음을 다음 가사로 본 경계 {sustained_guards}곳을 "
                "서로 다른 정렬 경로로 재검증함"
            )

        if auto_segment:
            segmented = auto_segment_source_cues(
                cue_texts,
                source_cues,
                global_units,
                local_units_by_index=local_units_by_index,
                global_pause_indices={
                    match.cue_index
                    for match in transcript_matches
                    if match.status == "weak"
                },
                preferred_chars=30,
                hard_chars=50,
            )
            segmented, merge_count = merge_obvious_wrapped_lines(
                cue_texts,
                segmented,
                paragraph_barriers=paragraph_barriers,
                preferred_chars=30,
            )
            split_count = sum(len(items) - 1 for items in segmented.values())
            if split_count:
                log.append(
                    f"발화 속도와 명확한 공백을 기준으로 자막 {split_count}개를 추가 분할함"
                )
            if merge_count:
                log.append(
                    f"연속 발화로 확인된 자동 줄바꿈 {merge_count}곳을 합침"
                )
        else:
            segmented = {index: [cue] for index, cue in source_cues.items()}

        auto_hidden_by_after = {
            gap.after_cue_index: Cue(
                text=_mark_hidden(gap.text), start=gap.start, end=gap.end
            )
            for gap in auto_hidden_gaps
        }
        source_order_items: list[tuple[int, Cue]] = []
        for index in range(len(cue_texts)):
            source_order_items.extend((index, cue) for cue in segmented.get(index, []))
            auto_hidden = auto_hidden_by_after.get(index)
            if auto_hidden is not None:
                source_order_items.append((index, auto_hidden))
        if not source_order_items:
            raise RuntimeError("No lyric cues could be aligned to the audio")

        raw_cues, reversed_indices = _preserve_source_order(source_order_items)
        if reversed_indices:
            lines = ", ".join(str(index + 1) for index in reversed_indices)
            log.append(
                f"원문 순서를 거스르는 정렬이라 제외한 줄: {lines}. "
                "실제 가창의 절 순서가 원문과 다른지 확인해 주세요."
            )

        polished_all = polish_singing_cue_times(
            raw_cues,
            activity=activity,
            lead_ms=lead_ms,
            end_hold_ms=end_pad_ms,
            min_duration_ms=min_duration_ms,
            max_duration_ms=max_duration_ms,
            min_gap_ms=min_gap_ms,
        )
        hidden_timing_cues = [cue for cue in polished_all if _is_hidden(cue)]
        cues = [cue for cue in polished_all if not _is_hidden(cue)]
        if not cues:
            raise RuntimeError("No visible lyric cues remained after alignment")

        for match in transcript_matches:
            if match.cue_index in hidden_source_indices:
                continue
            if match.status == "changed" and match.similarity < 0.78:
                log.append(
                    f"원문 {match.cue_index + 1}줄 유지: "
                    f"‘{match.source_text}’ / ASR ‘{match.transcript_text}’"
                )
            elif match.status == "weak":
                log.append(
                    f"원문 {match.cue_index + 1}줄 확인 필요: ASR 일치도 "
                    f"{match.similarity:.0%}"
                )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_srt(
            cues,
            offset_seconds=offset_seconds + range_start,
            timeline_anchor=timeline_anchor,
        ),
        encoding="utf-8-sig",
    )
    if debug_json:
        payload = {
            "audio": str(audio_path.resolve()),
            "duration": duration,
            "backend": "stable-ts-hybrid-auto" if auto_segment else "stable-ts-hybrid",
            "model": model_name,
            "language": language,
            "detected_language": detected_language,
            "device": asdict(device_choice),
            "settings": {
                "auto_segment": auto_segment,
                "timeline_anchor": timeline_anchor,
                "max_chars": max_chars,
                "auto_preferred_chars": 30,
                "auto_hard_chars": 50,
                "lead_ms": lead_ms,
                "end_hold_ms": end_pad_ms,
                "min_duration_ms": min_duration_ms,
                "max_duration_ms": max_duration_ms,
                "min_gap_ms": min_gap_ms,
                "range_start_seconds": range_start,
                "range_end_seconds": range_end_seconds,
            },
            "transcript_units": [asdict(unit) for unit in transcript_units],
            "transcript_matches": [asdict(match) for match in transcript_matches],
            "auto_hidden_gaps": [asdict(gap) for gap in auto_hidden_gaps],
            "manual_hidden_indices": sorted(hidden_source_indices),
            "global_units": [asdict(unit) for unit in global_units],
            "local_cues": {
                str(index): asdict(cue) for index, cue in local_cues.items()
            },
            "local_units": {
                str(index): [asdict(unit) for unit in units]
                for index, units in local_units_by_index.items()
            },
            "start_adjustments": [
                asdict(adjustment) for adjustment in start_adjustments
            ],
            "hidden_timing_cues": [
                {
                    "text": _unmark_hidden(cue.text),
                    "start": cue.start,
                    "end": cue.end,
                }
                for cue in hidden_timing_cues
            ],
            "raw_cues": [asdict(cue) for cue in raw_cues if not _is_hidden(cue)],
            "cues": [asdict(cue) for cue in cues],
            "messages": log,
        }
        Path(debug_json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return cues


def _mark_hidden(text: str) -> str:
    return f"{_HIDDEN_PREFIX}{text}"


def _is_hidden(cue: Cue) -> bool:
    return cue.text.startswith(_HIDDEN_PREFIX)


def _unmark_hidden(text: str) -> str:
    return text[len(_HIDDEN_PREFIX) :] if text.startswith(_HIDDEN_PREFIX) else text


def _preserve_source_order(
    items: Sequence[tuple[int, Cue]],
    *,
    reversal_tolerance: float = 0.25,
) -> tuple[list[Cue], list[int]]:
    kept: list[Cue] = []
    rejected: list[int] = []
    previous_group_start = -1.0
    position = 0
    while position < len(items):
        source_index = items[position][0]
        group: list[Cue] = []
        while position < len(items) and items[position][0] == source_index:
            group.append(items[position][1])
            position += 1
        if not group:
            continue
        group_start = group[0].start
        if group_start < previous_group_start - reversal_tolerance:
            rejected.append(source_index)
            continue
        kept.extend(group)
        previous_group_start = max(previous_group_start, group_start)
    return kept, rejected



def _partial_lyric_span(
    matches: Sequence[CueTranscriptMatch],
) -> tuple[int, int] | None:
    """Return the conservative continuous source span heard in a partial clip."""
    anchored = [match.cue_index for match in matches if match.usable_anchor]
    if not anchored:
        return None
    return min(anchored), max(anchored)

def _select_window_matches(
    matches: Sequence[CueTranscriptMatch],
    global_cues: Sequence[Cue | None],
) -> list[CueTranscriptMatch]:
    del global_cues
    return [
        match
        for match in matches
        if match.start is not None
        and match.end is not None
        and match.exact_characters >= 2
        and match.similarity >= 0.62
        and match.coverage >= 0.45
    ]


def _guard_lexical_start(cue: Cue, match: CueTranscriptMatch) -> Cue:
    guarded, _ = refine_start_from_evidence(0, cue, match)
    return guarded


def demo_to_srt(
    audio_path: str | Path,
    lyrics_text: str,
    output_path: str | Path,
    *,
    max_chars: int = 30,
) -> list[Cue]:
    with tempfile.TemporaryDirectory(prefix="lyrics-aligner-demo-") as temporary:
        source_wav = ensure_wav(audio_path, Path(temporary) / "resolve-audio.wav")
        duration = wav_duration(source_wav)
    cue_texts = split_lyrics(lyrics_text, max_chars=max_chars)
    if not cue_texts:
        raise ValueError("Lyrics are empty")
    slot = duration / len(cue_texts)
    cues = [
        Cue(text=text, start=index * slot, end=min(duration, (index + 1) * slot))
        for index, text in enumerate(cue_texts)
    ]
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_srt(cues), encoding="utf-8-sig")
    return cues
