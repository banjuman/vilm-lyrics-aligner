from __future__ import annotations

import json
import sys
import tempfile
import time
import uuid
from pathlib import Path


MODULES = Path(
    r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
)
sys.path.insert(0, str(MODULES))
import DaVinciResolveScript as dvr_script  # noqa: E402


def start_job(project, job_id: str) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for args in ((job_id,), ([job_id],), ([job_id], False), ([job_id], True)):
        try:
            started = bool(project.StartRendering(*args))
        except Exception as exc:
            errors.append(f"StartRendering{args!r}: {type(exc).__name__}: {exc}")
            continue
        if started or project.IsRenderingInProgress():
            return True, errors
        errors.append(f"StartRendering{args!r}: returned False")
    return False, errors


def main() -> int:
    resolve = dvr_script.scriptapp("Resolve")
    if resolve is None:
        raise RuntimeError("Resolve scripting connection is unavailable")
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline() if project else None
    if project is None or timeline is None:
        raise RuntimeError("Open a Resolve project and timeline first")

    formats = project.GetRenderFormats() or {}
    by_extension = {
        str(extension).casefold().lstrip("."): str(name)
        for name, extension in formats.items()
    }
    print("FORMATS=" + json.dumps(formats, ensure_ascii=False, sort_keys=True))
    for extension in ("wav", "mp3", "m4a", "aac", "mp4", "mov"):
        name = by_extension.get(extension)
        codecs = {}
        for query in dict.fromkeys(item for item in (extension, name) if item):
            codecs.update(project.GetRenderCodecs(query) or {})
        print(
            f"CODECS {extension}="
            + json.dumps(codecs, ensure_ascii=False, sort_keys=True)
        )

    candidates = [
        ("wav-pcm", "wav", ("LinearPCM", "LPCM"), "wav", "lpcm"),
        ("mp3", "mp3", ("mp3", "MP3"), "mp3", "mp3"),
        ("m4a-aac", "m4a", ("aac", "AAC"), "m4a", "aac"),
        ("mp4-aac", "mp4", ("H264", "H.264"), "mp4", "aac"),
        ("mov-aac", "mov", ("H264", "H.264"), "mov", "aac"),
        ("mov-lpcm", "mov", ("H264", "H.264"), "mov", "lpcm"),
    ]
    restore_preset = f"LyricsAligner probe restore {uuid.uuid4().hex}"
    preset_saved = bool(project.SaveAsNewRenderPreset(restore_preset))
    if not preset_saved:
        raise RuntimeError("Could not snapshot current render settings")
    original_mode = project.GetCurrentRenderMode()
    results: list[dict] = []

    try:
        with tempfile.TemporaryDirectory(prefix="lyrics-aligner-format-probe-") as directory:
            target = Path(directory)
            start = int(timeline.GetStartFrame())
            end = min(int(timeline.GetEndFrame()), start + 24)
            for label, extension, video_codecs, expected_extension, audio_codec in candidates:
                job_id = None
                selected = None
                attempts: list[str] = []
                try:
                    format_name = by_extension.get(extension)
                    for render_format in dict.fromkeys(
                        item for item in (extension, format_name) if item
                    ):
                        for video_codec in video_codecs:
                            attempts.append(f"{render_format}/{video_codec}")
                            if project.SetCurrentRenderFormatAndCodec(
                                render_format, video_codec
                            ):
                                selected = (render_format, video_codec)
                                break
                        if selected:
                            break
                    if not selected:
                        results.append(
                            {
                                "candidate": label,
                                "selected": False,
                                "attempts": attempts,
                            }
                        )
                        continue

                    project.SetCurrentRenderMode(1)
                    base_name = f"probe-{label}-{uuid.uuid4().hex}"
                    settings = {
                        "SelectAllFrames": False,
                        "MarkIn": start,
                        "MarkOut": end,
                        "TargetDir": str(target),
                        "CustomName": base_name,
                        "ExportVideo": False,
                        "ExportAudio": True,
                        "AudioCodec": audio_codec,
                        "AudioSampleRate": 48000,
                        "AudioBitDepth": 24,
                    }
                    settings_ok = bool(project.SetRenderSettings(settings))
                    if not settings_ok:
                        results.append(
                            {
                                "candidate": label,
                                "selected": selected,
                                "settings_ok": False,
                            }
                        )
                        continue

                    job_id = project.AddRenderJob()
                    if not job_id:
                        results.append(
                            {
                                "candidate": label,
                                "selected": selected,
                                "settings_ok": True,
                                "job_added": False,
                            }
                        )
                        continue
                    jobs = project.GetRenderJobList() or []
                    job = next(
                        (item for item in jobs if item.get("JobId") == job_id), None
                    )
                    started, errors = start_job(project, str(job_id))
                    if started:
                        deadline = time.monotonic() + 60
                        while project.IsRenderingInProgress() and time.monotonic() < deadline:
                            time.sleep(0.1)
                        if project.IsRenderingInProgress():
                            project.StopRendering()
                    status = project.GetRenderJobStatus(job_id) or {}
                    outputs = [
                        path.name
                        for path in target.glob(f"{base_name}*")
                        if path.is_file()
                    ]
                    results.append(
                        {
                            "candidate": label,
                            "selected": selected,
                            "settings_ok": True,
                            "job": job,
                            "started": started,
                            "start_errors": errors,
                            "status": status,
                            "outputs": outputs,
                            "expected_extension": expected_extension,
                        }
                    )
                except Exception as exc:
                    results.append(
                        {
                            "candidate": label,
                            "selected": selected,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                finally:
                    if job_id:
                        project.DeleteRenderJob(job_id)
    finally:
        project.LoadRenderPreset(restore_preset)
        project.DeleteRenderPreset(restore_preset)
        if original_mode is not None:
            project.SetCurrentRenderMode(original_mode)

    print("RESULTS=" + json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
