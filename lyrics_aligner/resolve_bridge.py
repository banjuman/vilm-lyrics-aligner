from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class ResolveBridgeError(RuntimeError):
    pass


class RenderCancelled(ResolveBridgeError):
    pass


@dataclass(frozen=True)
class TimelineRange:
    start_frame: int
    end_frame: int
    used_marks: bool


@dataclass(frozen=True)
class _RenderCandidate:
    label: str
    extension: str
    format_extensions: tuple[str, ...]
    codec_fallbacks: tuple[str, ...]
    export_video: bool
    audio_codec: str | None = None


def choose_timeline_range(timeline, use_marks: bool = True) -> TimelineRange:
    timeline_start = int(timeline.GetStartFrame())
    if use_marks:
        marks = timeline.GetMarkInOut() or {}
        for kind in ("audio", "video"):
            selected = marks.get(kind) or {}
            if "in" in selected and "out" in selected:
                # Resolve exposes timeline marks relative to the timeline start,
                # while Deliver MarkIn/MarkOut and AppendToTimeline recordFrame
                # expect absolute timeline frames (including start timecode).
                relative_start = int(selected["in"])
                relative_end = int(selected["out"])
                if relative_end >= relative_start:
                    return TimelineRange(
                        timeline_start + relative_start,
                        timeline_start + relative_end,
                        True,
                    )
    return TimelineRange(timeline_start, int(timeline.GetEndFrame()), False)



def _snapshot_timeline_marks(timeline) -> dict:
    marks = timeline.GetMarkInOut() or {}
    snapshot = {
        kind: {key: int(value) for key, value in selected.items() if key in {"in", "out"}}
        for kind, selected in marks.items()
        if isinstance(selected, dict) and kind in {"video", "audio"}
    }
    # Resolve can leave a full-timeline mark of the other media type after a
    # Deliver render. If a real partial range also exists, retaining that stale
    # full-range mark produces the separate blue/green bars seen in the Edit UI.
    timeline_start = int(timeline.GetStartFrame())
    full_range = (0, int(timeline.GetEndFrame()) - timeline_start)
    partial = {
        kind: selected
        for kind, selected in snapshot.items()
        if (selected.get("in"), selected.get("out")) != full_range
    }
    return partial or snapshot


def _restore_timeline_marks(timeline, marks: dict) -> None:
    try:
        timeline.ClearMarkInOut("all")
        video = marks.get("video") or {}
        audio = marks.get("audio") or {}
        if (
            "in" in video and "out" in video
            and video.get("in") == audio.get("in")
            and video.get("out") == audio.get("out")
        ):
            # Standard Edit-page In/Out sets both types together. Restore them
            # in one API call so one bar cannot be expanded independently.
            timeline.SetMarkInOut(video["in"], video["out"], "all")
            return
        for kind, selected in (("video", video), ("audio", audio)):
            if "in" in selected and "out" in selected:
                timeline.SetMarkInOut(selected["in"], selected["out"], kind)
    except Exception:
        # Mark restoration must not hide the actual render result/error.
        pass


def timeline_frame_rate(project, timeline) -> float:
    for owner in (timeline, project):
        try:
            raw = owner.GetSetting("timelineFrameRate")
            rate = float(str(raw).strip().split()[0])
            if rate > 0:
                return rate
        except (AttributeError, TypeError, ValueError, IndexError):
            continue
    raise ResolveBridgeError("Could not read the timeline frame rate")

def _codec_map(project, extension: str, name: str | None) -> dict:
    result = {}
    for query in (extension, name):
        if query:
            result.update(project.GetRenderCodecs(query) or {})
    return result


def _render_candidates(project) -> list[_RenderCandidate]:
    formats = project.GetRenderFormats() or {}
    available = {str(extension).casefold().lstrip(".") for extension in formats.values()}
    candidates = [
        _RenderCandidate(
            "Wave/PCM", "wav", ("wav",), ("LinearPCM", "LPCM"), False, "lpcm"
        )
    ]
    if "mp3" in available:
        candidates.append(
            _RenderCandidate("MP3 audio", "mp3", ("mp3",), ("mp3", "MP3"), False, "mp3")
        )
    for extension in ("m4a", "aac"):
        if extension in available:
            candidates.append(
                _RenderCandidate(
                    f"{extension.upper()} audio",
                    extension,
                    (extension,),
                    ("aac", "AAC"),
                    False,
                    "aac",
                )
            )
    candidates.append(
        _RenderCandidate(
            "QuickTime timeline mix",
            "mov",
            ("mov",),
            ("H264", "H.264", "ProRes422HQ"),
            True,
            None,
        )
    )
    return candidates


def _select_render_candidate(project, candidate: _RenderCandidate) -> tuple[str, str] | None:
    formats = project.GetRenderFormats() or {}
    by_extension = {
        str(extension).casefold().lstrip("."): str(name)
        for name, extension in formats.items()
    }
    for extension in candidate.format_extensions:
        name = by_extension.get(extension)
        codecs = _codec_map(project, extension, name)
        ranked: list[str] = []
        for description, codec in codecs.items():
            searchable = f"{description} {codec}".casefold()
            if any(item.casefold() in searchable for item in candidate.codec_fallbacks):
                ranked.append(str(codec))
        ranked.extend(candidate.codec_fallbacks)
        for render_format in dict.fromkeys(item for item in (extension, name) if item):
            for codec in dict.fromkeys(ranked):
                if project.SetCurrentRenderFormatAndCodec(render_format, codec):
                    return str(render_format), str(codec)
    return None


def _apply_render_settings(
    project,
    selected_range: TimelineRange,
    output_dir: Path,
    base_name: str,
    candidate: _RenderCandidate,
) -> None:
    range_settings = (
        {
            "SelectAllFrames": False,
            "MarkIn": selected_range.start_frame,
            "MarkOut": selected_range.end_frame,
        }
        if selected_range.used_marks
        else {"SelectAllFrames": True}
    )
    settings = {
        **range_settings,
        "TargetDir": str(output_dir),
        "CustomName": base_name,
        "ExportVideo": candidate.export_video,
        "ExportAudio": True,
    }
    if candidate.audio_codec:
        settings.update(
            {
                "AudioCodec": candidate.audio_codec,
                "AudioSampleRate": 48000,
                "AudioBitDepth": 24,
            }
        )
    if project.SetRenderSettings(settings):
        return
    common = {
        **range_settings,
        "TargetDir": str(output_dir),
        "CustomName": base_name,
    }
    if not project.SetRenderSettings(common):
        raise ResolveBridgeError(
            f"Resolve rejected basic temporary render settings: {common}"
        )
    audio_ok = bool(project.SetRenderSettings({"ExportAudio": True}))
    project.SetRenderSettings({"ExportVideo": candidate.export_video})
    if candidate.audio_codec:
        project.SetRenderSettings({"AudioCodec": candidate.audio_codec})
    if not audio_ok:
        raise ResolveBridgeError("Resolve would not enable audio for the temporary render")


def _start_render_job(project, job_id: str) -> None:
    """Start one render job across Resolve's slightly inconsistent bindings."""
    attempts = (
        (job_id,),
        ([job_id],),
        ([job_id], False),
        ([job_id], True),
    )
    errors = []
    for args in attempts:
        try:
            started = bool(project.StartRendering(*args))
        except Exception as exc:
            errors.append(f"StartRendering{args!r}: {type(exc).__name__}: {exc}")
            continue
        if started or project.IsRenderingInProgress():
            return
        errors.append(f"StartRendering{args!r}: returned False")

    jobs = project.GetRenderJobList() or []
    status = project.GetRenderJobStatus(job_id) or {}
    raise ResolveBridgeError(
        "Resolve could not start the temporary audio render. "
        f"attempts={errors}; job_status={status}; render_jobs={jobs}"
    )


def _wait_for_render(
    project,
    job_id: str,
    timeout_seconds: float,
    cancel_requested: Callable[[], bool] | None = None,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while project.IsRenderingInProgress():
        if cancel_requested is not None and cancel_requested():
            project.StopRendering()
            raise RenderCancelled("Timeline audio render cancelled")
        if time.monotonic() >= deadline:
            project.StopRendering()
            raise ResolveBridgeError("Timed out while rendering the timeline audio")
        time.sleep(0.25)
    status = project.GetRenderJobStatus(job_id) or {}
    job_status = str(status.get("JobStatus", "")).casefold()
    if job_status and job_status not in {"complete", "completed"}:
        raise ResolveBridgeError(f"Resolve audio render did not complete: {status}")


def _find_render_output(output_dir: Path, base_name: str, extension: str) -> Path:
    expected = output_dir / f"{base_name}.{extension}"
    if expected.exists():
        return expected
    matches = sorted(path for path in output_dir.glob(f"{base_name}.*") if path.is_file())
    if len(matches) == 1:
        return matches[0]
    raise ResolveBridgeError(
        f"Resolve finished but the temporary render was not found in {output_dir}"
    )


def render_timeline_audio(
    project,
    timeline,
    output_dir: str | Path,
    *,
    use_marks: bool = True,
    timeout_seconds: float = 900,
    cancel_requested: Callable[[], bool] | None = None,
) -> tuple[Path, TimelineRange]:
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    original_marks = _snapshot_timeline_marks(timeline)
    selected_range = choose_timeline_range(timeline, use_marks=use_marks)
    restore_preset = f"LyricsAligner restore {uuid.uuid4().hex}"
    original_format = project.GetCurrentRenderFormatAndCodec() or {}
    original_mode = project.GetCurrentRenderMode()
    preset_saved = False
    errors: list[str] = []

    try:
        preset_saved = bool(project.SaveAsNewRenderPreset(restore_preset))
        if not preset_saved:
            raise ResolveBridgeError("Could not snapshot the current Resolve render settings")

        for candidate in _render_candidates(project):
            if cancel_requested is not None and cancel_requested():
                raise RenderCancelled("Timeline audio render cancelled")
            job_id = None
            base_name = f"lyrics-aligner-{uuid.uuid4().hex}"
            try:
                if not project.LoadRenderPreset(restore_preset):
                    raise ResolveBridgeError("Could not restore render settings between attempts")
                selected = _select_render_candidate(project, candidate)
                if selected is None:
                    errors.append(f"{candidate.label}: format/codec unavailable")
                    continue
                if not project.SetCurrentRenderMode(1):
                    raise ResolveBridgeError("Could not switch Resolve to Single Clip render mode")
                _apply_render_settings(
                    project, selected_range, output_dir, base_name, candidate
                )
                job_id = project.AddRenderJob()
                if not job_id:
                    raise ResolveBridgeError("Resolve could not add the temporary render job")
                _start_render_job(project, str(job_id))
                _wait_for_render(
                    project,
                    str(job_id),
                    timeout_seconds,
                    cancel_requested=cancel_requested,
                )
                return _find_render_output(
                    output_dir, base_name, candidate.extension
                ), selected_range
            except RenderCancelled:
                raise
            except Exception as exc:
                errors.append(f"{candidate.label}: {exc}")
                for partial in output_dir.glob(f"{base_name}*"):
                    if partial.is_file():
                        try:
                            partial.unlink()
                        except OSError:
                            pass
            finally:
                if job_id:
                    project.DeleteRenderJob(job_id)

        raise ResolveBridgeError(
            "Resolve could not render a usable timeline audio file. " + " | ".join(errors)
        )
    finally:
        if preset_saved:
            project.LoadRenderPreset(restore_preset)
            project.DeleteRenderPreset(restore_preset)
        elif original_format.get("format") and original_format.get("codec"):
            project.SetCurrentRenderFormatAndCodec(
                original_format["format"], original_format["codec"]
            )
        if original_mode is not None:
            project.SetCurrentRenderMode(original_mode)
        # Loading the saved Deliver preset can itself change visible marks in
        # some Resolve versions, so mark restoration must be the final step.
        _restore_timeline_marks(timeline, original_marks)


def import_srt_to_timeline(project, timeline, srt_path: str | Path, record_frame: int):
    srt_path = Path(srt_path).resolve()
    if not srt_path.is_file():
        raise FileNotFoundError(srt_path)
    media_pool = project.GetMediaPool()
    imported = media_pool.ImportMedia([str(srt_path)]) or []
    if not imported:
        raise ResolveBridgeError("Resolve could not import the generated SRT into the Media Pool")
    if timeline.GetTrackCount("subtitle") < 1:
        timeline.AddTrack("subtitle")
    appended = media_pool.AppendToTimeline(
        [{"mediaPoolItem": imported[0], "recordFrame": int(record_frame)}]
    )
    if not appended:
        raise ResolveBridgeError(
            "SRT was imported into the Media Pool, but Resolve did not append it to the timeline"
        )
    return appended
