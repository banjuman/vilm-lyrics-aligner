from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path


WIN_ID = "com.oho.lyricsaligner"
APP_DISPLAY_NAME = "Vilm Lyrics Aligner"
DEFAULT_UI_LANGUAGE = "en"
if sys.platform == "darwin":
    APP_DIR = Path.home() / "Library" / "Application Support" / "Vilm Lyrics Aligner"
else:
    APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LyricsAligner"
CONFIG_PATH = APP_DIR / "config.json"
PREFERENCES_PATH = APP_DIR / "preferences.json"
TRACE_PATH = APP_DIR / "last-run.log"


TEXT = {
    "ko": {
        "intro": "현재 타임라인의 노래에 원문 가사를 정렬합니다.",
        "lyrics": "가사 원문",
        "placeholder": "줄바꿈이 포함된 전체 가사를 붙여넣으세요.",
        "load": "가사 TXT 불러오기",
        "mode": "작업 모드",
        "auto_mode": "자동 모드",
        "manual_mode": "수동(고급) 모드",
        "auto_desc": "줄바꿈과 발화 공백을 참고해 자막을 자동 구성합니다.",
        "manual_desc": "가사 한 줄을 자막 하나로 유지하고 표시 방식을 직접 조절합니다.",
        "max_chars": "최대 글자 수",
        "max_duration": "최대 표시",
        "end_hold": "끝 여운",
        "device": "처리 장치",
        "cuda_device": "CUDA · NVIDIA (권장)",
        "metal_device": "Apple GPU · Metal (권장)",
        "cpu_device": "CPU",
        "accelerator_unavailable": "이 환경에서 사용할 수 있는 검증된 GPU 가속이 없습니다.",
        "device_hint_cuda": "CUDA가 기본입니다. 문제 해결이 필요할 때만 CPU를 선택하세요.",
        "device_hint_mps": "Apple Silicon에서는 Metal이 기본입니다. 문제가 있을 때만 CPU를 선택하세요.",
        "device_hint_cpu": "이 환경에서는 CPU로 처리합니다. 노래 길이에 따라 오래 걸릴 수 있습니다.",
        "short": "짧게 · 0.3초",
        "normal": "보통 · 0.5초",
        "long": "길게 · 1.0초",
        "very_long": "아주 길게 · 1.5초",
        "range": "처리 범위",
        "full_timeline": "전체 타임라인",
        "in_out": "In/Out 구간",
        "range_full_hint": "현재 타임라인 전체를 처리합니다.",
        "range_inout_hint": "타임라인에 설정한 In/Out 구간만 처리합니다.",
        "help": "사용법",
        "help_text": "1. 전체 가사를 붙여넣습니다.\n2. 대부분 자동 모드를 사용합니다.\n3. 필요하면 In/Out으로 구간을 제한합니다.\n4. 자막 생성을 누르면 현재 타임라인에 추가됩니다.",
        "generate": "자막 생성",
        "idle": "대기 중",
        "need_lyrics": "가사를 입력해 주세요.",
        "need_timeline": "현재 프로젝트와 타임라인을 찾을 수 없습니다.",
        "need_inout": "In/Out 구간을 먼저 설정해 주세요.",
        "existing_subtitles": "기존 자막은 유지되고 새 자막이 추가됩니다.",
        "step1": "1/3 타임라인 오디오를 준비하는 중…",
        "step2": "2/3 보컬 분리·원문 비교·타이밍 정렬 중…",
        "step3": "3/3 생성한 SRT를 현재 타임라인에 넣는 중…",
        "complete": "완료 — 현재 타임라인에 자막을 추가했습니다.",
        "output_file": "SRT 파일",
        "import_failed": "SRT 생성 완료. 자동 배치만 실패했습니다. 자세한 내용은 로그를 확인해 주세요.\n파일: {path}",
        "failed": "작업에 실패했습니다. 자세한 내용은 로그를 확인해 주세요.",
        "text_filter": "텍스트 파일 (*.txt)",
        "config_missing": "설정 파일이 없습니다: {path}",
        "project_missing": "프로젝트 폴더를 찾을 수 없습니다: {path}",
        "python_missing": "정렬 엔진 Python을 찾을 수 없습니다: {path}",
    },
    "en": {
        "intro": "Align the original lyrics to the song on the current timeline.",
        "lyrics": "Original lyrics",
        "placeholder": "Paste the full lyrics, including line breaks.",
        "load": "Load lyrics TXT",
        "mode": "Mode",
        "auto_mode": "Auto mode",
        "manual_mode": "Manual (advanced)",
        "auto_desc": "Build subtitle cues automatically from line breaks and vocal pauses.",
        "manual_desc": "Keep each lyric line as one cue and adjust its display settings.",
        "max_chars": "Maximum characters",
        "max_duration": "Maximum duration",
        "end_hold": "End hold",
        "device": "Processing device",
        "cuda_device": "CUDA · NVIDIA (recommended)",
        "metal_device": "Apple GPU · Metal (recommended)",
        "cpu_device": "CPU",
        "accelerator_unavailable": "No verified GPU accelerator is available in this installation.",
        "device_hint_cuda": "CUDA is the default. Choose CPU only when troubleshooting.",
        "device_hint_mps": "Metal is the default on Apple silicon. Choose CPU only when troubleshooting.",
        "device_hint_cpu": "This system will use CPU processing, which can take longer for full songs.",
        "short": "Short · 0.3 sec",
        "normal": "Normal · 0.5 sec",
        "long": "Long · 1.0 sec",
        "very_long": "Very long · 1.5 sec",
        "range": "Range",
        "full_timeline": "Full timeline",
        "in_out": "In/Out range",
        "range_full_hint": "Process the entire current timeline.",
        "range_inout_hint": "Process only the In/Out range set on the timeline.",
        "help": "Help",
        "help_text": "1. Paste the full lyrics.\n2. Use Auto mode for most songs.\n3. Set In/Out when you only need part of the timeline.\n4. Generate subtitles to add them to the current timeline.",
        "generate": "Generate subtitles",
        "idle": "Ready",
        "need_lyrics": "Enter the lyrics first.",
        "need_timeline": "No current project or timeline was found.",
        "need_inout": "Set a timeline In/Out range first.",
        "existing_subtitles": "Existing subtitles will remain and new subtitles will be added.",
        "step1": "1/3 Preparing timeline audio…",
        "step2": "2/3 Separating vocals and aligning the original lyrics…",
        "step3": "3/3 Adding the generated SRT to the timeline…",
        "complete": "Complete — subtitles were added to the current timeline.",
        "output_file": "SRT file",
        "import_failed": "SRT created, but automatic placement failed. See the log for details.\nFile: {path}",
        "failed": "The job failed. See the log for technical details.",
        "text_filter": "Text files (*.txt)",
        "config_missing": "Configuration file not found: {path}",
        "project_missing": "Project folder not found: {path}",
        "python_missing": "Alignment engine Python not found: {path}",
    },
}


def load_config():
    if not CONFIG_PATH.is_file():
        raise RuntimeError(TEXT[ui_language]["config_missing"].format(path=CONFIG_PATH))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    project_root = Path(config["project_root"])
    python_exe = Path(config["python"])
    if not project_root.is_dir():
        raise RuntimeError(TEXT[ui_language]["project_missing"].format(path=project_root))
    if not python_exe.is_file():
        raise RuntimeError(TEXT[ui_language]["python_missing"].format(path=python_exe))
    return config, project_root, python_exe


def load_preferences():
    try:
        data = json.loads(PREFERENCES_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"ui_language": DEFAULT_UI_LANGUAGE}


preferences = load_preferences()
ui_language = preferences.get("ui_language", DEFAULT_UI_LANGUAGE)
if ui_language not in TEXT:
    ui_language = DEFAULT_UI_LANGUAGE

config, project_root, python_exe = load_config()
installed_backend = str(config.get("backend", "cpu")).strip().casefold()
if installed_backend not in {"cuda", "mps", "cpu"}:
    installed_backend = "cpu"
sys.path.insert(0, str(project_root))
from lyrics_aligner import resolve_bridge  # noqa: E402
from lyrics_aligner.cleanup import cleanup_old_diagnostics, cleanup_stale_workdirs  # noqa: E402
from lyrics_aligner.process_runner import run_streaming_process  # noqa: E402

try:
    cleanup_stale_workdirs()
    cleanup_old_diagnostics(APP_DIR / "Diagnostics")
except Exception:
    pass

ui = fusion.UIManager
dispatcher = bmd.UIDispatcher(ui)

existing = ui.FindWindow(WIN_ID)
if existing:
    existing.Show()
    existing.Raise()
    raise SystemExit

win = dispatcher.AddWindow(
    {
        "ID": WIN_ID,
        "Geometry": [120, 120, 720, 730],
        "WindowTitle": APP_DISPLAY_NAME,
    },
    ui.VGroup({"Spacing": 8}, [
        ui.HGroup({"Weight": 0, "Spacing": 8}, [
            ui.Label({"ID": "intro", "Weight": 0.62}),
            ui.Button({"ID": "helpButton", "Weight": 0.16}),
            ui.ComboBox({"ID": "uiLanguage", "Weight": 0.22}),
        ]),
        ui.VGroup({"ID": "helpGroup", "Hidden": True, "Weight": 0}, [
            ui.Label({"ID": "helpText", "WordWrap": True, "Weight": 0}),
        ]),
        ui.Label({"ID": "lyricsLabel", "Weight": 0}),
        ui.TextEdit({
            "ID": "lyrics",
            "AcceptRichText": False,
            "Weight": 1,
        }),
        ui.Button({"ID": "loadLyrics", "Weight": 0}),
        ui.HGroup({"Weight": 0, "Spacing": 8}, [
            ui.Label({"ID": "modeLabel", "Weight": 0.25}),
            ui.ComboBox({"ID": "modeSelector", "Weight": 0.75}),
        ]),
        ui.Label({"ID": "modeDescription", "WordWrap": True, "Weight": 0}),
        ui.VGroup({"ID": "manualGroup", "Hidden": True, "Weight": 0, "Spacing": 6}, [
            ui.HGroup({"Weight": 0, "Spacing": 8}, [
                ui.Label({"ID": "maxCharsLabel", "Weight": 0.35}),
                ui.SpinBox({
                    "ID": "maxChars",
                    "Value": 30,
                    "Minimum": 1,
                    "Maximum": 80,
                    "Weight": 0.15,
                }),
                ui.Label({"ID": "maxDurationLabel", "Weight": 0.35}),
                ui.SpinBox({
                    "ID": "maxDuration",
                    "Value": 10,
                    "Minimum": 3,
                    "Maximum": 30,
                    "Weight": 0.15,
                }),
            ]),
            ui.HGroup({"Weight": 0, "Spacing": 8}, [
                ui.Label({"ID": "endHoldLabel", "Weight": 0.35}),
                ui.ComboBox({"ID": "endHold", "Weight": 0.65}),
            ]),
        ]),
        ui.HGroup({"Weight": 0, "Spacing": 8}, [
            ui.Label({"ID": "deviceLabel", "Weight": 0.25}),
            ui.ComboBox({"ID": "deviceSelector", "Weight": 0.75}),
        ]),
        ui.Label({"ID": "deviceHint", "WordWrap": True, "Weight": 0}),
        ui.HGroup({"Weight": 0, "Spacing": 8}, [
            ui.Label({"ID": "rangeLabel", "Weight": 0.25}),
            ui.ComboBox({"ID": "rangeSelector", "Weight": 0.75}),
        ]),
        ui.Label({"ID": "rangeHint", "WordWrap": True, "Weight": 0}),
        ui.Button({"ID": "generate", "Weight": 0}),
        ui.Label({"ID": "status", "WordWrap": True, "Weight": 0}),
        ui.TextEdit({"ID": "log", "ReadOnly": True, "Weight": 0.30}),
    ]),
)

win.Find("uiLanguage").AddItems(["한국어", "English"])
win.Find("uiLanguage").CurrentIndex = 0 if ui_language == "ko" else 1

updating_ui = False
help_open = False
job_running = False
current_status_key = "idle"
current_status_values = {}


def tr(key, **values):
    return TEXT[ui_language][key].format(**values)


def trace(message):
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat(timespec="milliseconds")
        thread_name = threading.current_thread().name
        with TRACE_PATH.open("a", encoding="utf-8") as stream:
            stream.write(f"{timestamp} [{thread_name}] {message}\n")
    except Exception:
        pass


def begin_trace():
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        TRACE_PATH.write_text("", encoding="utf-8")
    except Exception:
        pass
    trace("run requested")


def set_combo_items(control_id, items, index):
    control = win.Find(control_id)
    control.Clear()
    control.AddItems(items)
    control.CurrentIndex = max(0, min(index, len(items) - 1))


def selected_device():
    if installed_backend not in {"cuda", "mps"}:
        return "cpu"
    # The installed accelerator is index 0 and CPU is index 1. Before items
    # are populated Resolve reports a negative index, so keep the default.
    return "cpu" if win.Find("deviceSelector").CurrentIndex == 1 else installed_backend


def update_context_text():
    win.Find("modeDescription").Text = tr("auto_desc" if is_automatic() else "manual_desc")
    win.Find("rangeHint").Text = tr(
        "range_inout_hint" if win.Find("rangeSelector").CurrentIndex == 1 else "range_full_hint"
    )


def apply_ui_language():
    global updating_ui
    updating_ui = True
    mode_index = win.Find("modeSelector").CurrentIndex
    range_index = win.Find("rangeSelector").CurrentIndex
    hold_index = win.Find("endHold").CurrentIndex
    device = selected_device()
    if hold_index < 0:
        hold_index = 1
    win.Find("intro").Text = tr("intro")
    win.Find("lyricsLabel").Text = tr("lyrics")
    win.Find("lyrics").PlaceholderText = tr("placeholder")
    win.Find("loadLyrics").Text = tr("load")
    win.Find("modeLabel").Text = tr("mode")
    win.Find("helpButton").Text = tr("help")
    win.Find("helpText").Text = tr("help_text")
    win.Find("maxCharsLabel").Text = tr("max_chars")
    win.Find("maxDurationLabel").Text = tr("max_duration")
    win.Find("endHoldLabel").Text = tr("end_hold")
    win.Find("deviceLabel").Text = tr("device")
    win.Find("rangeLabel").Text = tr("range")
    win.Find("generate").Text = tr("generate")
    win.Find("status").Text = tr(current_status_key, **current_status_values)
    win.Find("maxChars").Suffix = " 자" if ui_language == "ko" else " chars"
    win.Find("maxDuration").Suffix = " 초" if ui_language == "ko" else " sec"
    set_combo_items("modeSelector", [tr("auto_mode"), tr("manual_mode")], mode_index)
    set_combo_items(
        "endHold",
        [tr("short"), tr("normal"), tr("long"), tr("very_long")],
        hold_index,
    )
    set_combo_items("rangeSelector", [tr("full_timeline"), tr("in_out")], range_index)
    accelerator_key = "cuda_device" if installed_backend == "cuda" else "metal_device"
    device_items = (
        [tr(accelerator_key), tr("cpu_device")]
        if installed_backend in {"cuda", "mps"}
        else [tr("cpu_device")]
    )
    device_index = 0 if device in {"cuda", "mps"} else len(device_items) - 1
    set_combo_items("deviceSelector", device_items, device_index)
    win.Find("deviceSelector").ToolTip = (
        "" if installed_backend in {"cuda", "mps"} else tr("accelerator_unavailable")
    )
    hint_key = (
        f"device_hint_{installed_backend}"
        if installed_backend in {"cuda", "mps"}
        else "device_hint_cpu"
    )
    win.Find("deviceHint").Text = tr(hint_key)
    update_context_text()
    updating_ui = False


def save_preferences():
    PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREFERENCES_PATH.write_text(
        json.dumps(
            {"ui_language": ui_language},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def set_status(key, **values):
    global current_status_key, current_status_values
    current_status_key = key
    current_status_values = values
    message = tr(key, **values)
    win.Find("status").Text = message
    win.Find("log").Append(str(message))


def is_automatic():
    return win.Find("modeSelector").CurrentIndex == 0


def update_options(ev=None):
    manual = not is_automatic()
    win.Find("manualGroup").Hidden = not manual
    win.Find("helpGroup").Hidden = not help_open
    update_context_text()
    win.RecalcLayout()
    height = (850 if manual else 730) + (110 if help_open else 0)
    win.Resize([720, height])
    win.RecalcLayout()


def on_mode_changed(ev):
    if not updating_ui:
        update_options()


def on_range_changed(ev):
    if not updating_ui:
        update_context_text()


def on_help_clicked(ev):
    global help_open
    help_open = not help_open
    update_options()


def on_ui_language_changed(ev):
    global ui_language
    if updating_ui:
        return
    ui_language = "ko" if win.Find("uiLanguage").CurrentIndex == 0 else "en"
    apply_ui_language()
    update_options()
    save_preferences()


def load_lyrics(ev):
    selected = fusion.RequestFile("", "", {"FReqB_Filter": tr("text_filter")})
    if selected:
        win.Find("lyrics").PlainText = Path(str(selected)).read_text(encoding="utf-8-sig")


def run_alignment_sync(options):
    trace("synchronous alignment entered")
    documents = Path.home() / "Documents" / "Lyrics Aligner"
    documents.mkdir(parents=True, exist_ok=True)
    diagnostics = APP_DIR / "Diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    safe_timeline = "".join(
        character if character not in r'<>:"/\\|?*' else "_"
        for character in options["timeline_name"]
    )
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_srt = documents / f"{safe_timeline}-{stamp}.srt"
    debug_json = diagnostics / f"{safe_timeline}-{stamp}.json"
    command = [
        str(python_exe), "-m", "lyrics_aligner", "align",
        str(options["media_path"]), str(options["lyrics_path"]),
        "-o", str(output_srt), "--max-chars", str(options["max_chars"]),
    ]
    if options["automatic"]:
        command.append("--auto-segment")
    if options["partial_range"]:
        command.append("--partial-range")
    command.extend(["--offset-seconds", str(options["offset_seconds"])])
    command.extend([
        "--max-duration-ms",
        str(10000 if options["automatic"] else options["max_duration_ms"]),
        "--min-gap-ms", "80", "--end-pad-ms",
        str(500 if options["automatic"] else options["end_pad_ms"]),
        "--debug-json", str(debug_json),
    ])
    child_env = os.environ.copy()
    child_env["PYTHONUTF8"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"
    child_env["PYTHONUNBUFFERED"] = "1"
    child_env["LYRICS_ALIGNER_DEVICE"] = options["device"]
    trace(f"device selected: {options['device']}")

    def forward_output(line):
        trace(f"engine output: {line[:240]}")
        win.Find("log").Append(str(line))
        try:
            win.Repaint()
        except Exception:
            pass

    trace(f"starting engine synchronously: partial_range={options['partial_range']}")
    result = run_streaming_process(
        command,
        cwd=project_root,
        env=child_env,
        on_output=forward_output,
    )
    trace(f"engine returned: code={result.returncode}")
    if result.returncode != 0:
        raise RuntimeError(result.output.strip() or "Alignment engine failed")
    return output_srt


def on_generate(ev):
    global job_running
    begin_trace()
    if job_running:
        return
    lyrics = win.Find("lyrics").PlainText.strip()
    if not lyrics:
        set_status("need_lyrics")
        return
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline() if project else None
    if not project or not timeline:
        set_status("need_timeline")
        return
    bridge = importlib.reload(resolve_bridge)
    use_marks = win.Find("rangeSelector").CurrentIndex == 1
    selected_range = bridge.choose_timeline_range(timeline, use_marks=use_marks)
    try:
        raw_marks = timeline.GetMarkInOut() or {}
    except Exception as exc:
        raw_marks = {"error": str(exc)}
    trace(
        f"range: use_marks={use_marks}, raw={raw_marks}, "
        f"selected={selected_range.start_frame}-{selected_range.end_frame}, "
        f"used_marks={selected_range.used_marks}"
    )
    if use_marks and not selected_range.used_marks:
        set_status("need_inout")
        return
    try:
        if timeline.GetTrackCount("subtitle") > 0:
            win.Find("log").Append(tr("existing_subtitles"))
    except Exception:
        pass

    automatic = is_automatic()
    temp_path = Path(tempfile.mkdtemp(prefix="lyrics-aligner-resolve-"))
    lyrics_path = temp_path / "lyrics.txt"
    lyrics_path.write_text(lyrics, encoding="utf-8")
    job_running = True
    win.Find("generate").Enabled = False
    try:
        set_status("step1")
        media_path, selected_range = bridge.render_timeline_audio(
            project, timeline, temp_path, use_marks=use_marks
        )
        trace(
            f"render complete: path={media_path}, bytes={media_path.stat().st_size}, "
            f"range={selected_range.start_frame}-{selected_range.end_frame}"
        )
        frame_rate = bridge.timeline_frame_rate(project, timeline)
        offset_seconds = (
            selected_range.start_frame - int(timeline.GetStartFrame())
        ) / frame_rate
        trace(f"subtitle offset: {offset_seconds:.3f}s at {frame_rate}fps")
        options = {
            "timeline_name": timeline.GetName(),
            "media_path": media_path,
            "lyrics_path": lyrics_path,
            "partial_range": selected_range.used_marks,
            "offset_seconds": offset_seconds,
            "device": selected_device(),
            "automatic": automatic,
            "max_chars": int(win.Find("maxChars").Value),
            "max_duration_ms": int(win.Find("maxDuration").Value) * 1000,
            "end_pad_ms": [300, 500, 1000, 1500][win.Find("endHold").CurrentIndex],
        }
        set_status("step2")
        output_srt = run_alignment_sync(options)
        set_status("step3")
        try:
            bridge.import_srt_to_timeline(
                project, timeline, output_srt, int(timeline.GetStartFrame())
            )
        except bridge.ResolveBridgeError as exc:
            win.Find("log").Append(f"{type(exc).__name__}: {exc}")
            set_status("import_failed", path=output_srt)
            return
        win.Find("log").Append(f"{tr('output_file')}: {output_srt}")
        set_status("complete")
        trace("job completed")
    except Exception as exc:
        trace(f"job failed: {type(exc).__name__}: {exc}")
        win.Find("log").Append(f"{type(exc).__name__}: {exc}")
        set_status("failed")
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)
        win.Find("generate").Enabled = True
        job_running = False


def on_close(ev):
    trace("panel close requested")
    dispatcher.ExitLoop()


win.On[WIN_ID].Close = on_close
win.On["loadLyrics"].Clicked = load_lyrics
win.On["modeSelector"].CurrentIndexChanged = on_mode_changed
win.On["rangeSelector"].CurrentIndexChanged = on_range_changed
win.On["helpButton"].Clicked = on_help_clicked
win.On["uiLanguage"].CurrentIndexChanged = on_ui_language_changed
win.On["generate"].Clicked = on_generate
apply_ui_language()
update_options()
win.Show()
dispatcher.RunLoop()
