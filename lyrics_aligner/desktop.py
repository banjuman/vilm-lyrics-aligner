from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Canvas, StringVar, Text, Tk, filedialog, messagebox
from tkinter import ttk

from .media import waveform_peaks
from .platform_paths import application_data_root
from .process_runner import JobCancelled, run_streaming_process


APP_NAME = "Vilm Lyrics Aligner"
APP_DIR = application_data_root()
CONFIG_PATH = APP_DIR / "config.json"
PREFERENCES_PATH = APP_DIR / "desktop-preferences.json"

TEXT = {
    "en": {
        "media": "1. Media",
        "drop": "Choose the video or audio that matches the edit where subtitles will be used.",
        "browse": "Choose media…",
        "no_media": "No media selected",
        "range": "2. Processing range",
        "full": "Full file",
        "selection": "Selected waveform range",
        "range_help": "For a long file, drag across the waveform. Only the selected range is processed.",
        "lyrics": "3. Original lyrics",
        "lyrics_hint": "Paste the full lyrics. Vilm will locate the lines heard in a selected range.",
        "load": "Load TXT…",
        "mode": "4. Subtitle style",
        "auto": "Auto mode (recommended)",
        "manual": "Manual (advanced)",
        "max_chars": "Max characters",
        "max_duration": "Max duration (sec)",
        "end_hold": "End hold",
        "device": "Processing device",
        "generate": "Generate SRT",
        "cancel": "Cancel",
        "ready": "Ready",
        "loading": "Reading media and drawing waveform…",
        "processing": "Processing locally. Full songs can take several minutes.",
        "done": "SRT created successfully.",
        "open_folder": "Open output folder",
        "need_media": "Choose a media file first.",
        "need_lyrics": "Paste the original lyrics first.",
        "bad_range": "Select a range of at least one second.",
        "save_title": "Save subtitle file",
        "file_error": "Could not read this media file",
        "failed": "Generation failed",
        "cancelled": "Cancelled",
        "guide": "Complex edited timeline? Use the NLE integration when available. Otherwise export a lightweight full-timeline reference audio file, then select only the needed range here.",
    },
    "ko": {
        "media": "1. 미디어",
        "drop": "자막을 사용할 편집본과 오디오 타이밍이 같은 영상 또는 음원을 선택하세요.",
        "browse": "영상·음원 선택…",
        "no_media": "선택한 미디어 없음",
        "range": "2. 처리 범위",
        "full": "전체 파일",
        "selection": "파형에서 선택한 구간",
        "range_help": "긴 파일은 파형을 드래그하세요. 선택한 구간만 AI가 처리합니다.",
        "lyrics": "3. 원문 가사",
        "lyrics_hint": "전체 가사를 붙여넣으세요. 선택 구간에서 들리는 줄은 Vilm이 찾습니다.",
        "load": "가사 TXT 불러오기…",
        "mode": "4. 자막 구성",
        "auto": "자동 모드 (권장)",
        "manual": "수동(고급) 모드",
        "max_chars": "최대 글자 수",
        "max_duration": "최대 표시(초)",
        "end_hold": "끝 여운",
        "device": "처리 장치",
        "generate": "SRT 생성",
        "cancel": "취소",
        "ready": "대기 중",
        "loading": "미디어를 읽고 파형을 만드는 중…",
        "processing": "로컬에서 처리 중입니다. 한 곡은 몇 분 걸릴 수 있습니다.",
        "done": "SRT를 생성했습니다.",
        "open_folder": "출력 폴더 열기",
        "need_media": "먼저 영상 또는 음원을 선택해 주세요.",
        "need_lyrics": "먼저 원문 가사를 붙여넣어 주세요.",
        "bad_range": "1초 이상의 구간을 선택해 주세요.",
        "save_title": "자막 파일 저장",
        "file_error": "미디어 파일을 읽지 못했습니다",
        "failed": "생성 실패",
        "cancelled": "취소됨",
        "guide": "복잡하게 편집된 타임라인은 가능하면 NLE 연동을 사용하세요. 연동할 수 없다면 가벼운 전체 타임라인 참고용 오디오를 출력한 뒤 필요한 구간만 여기서 선택하세요.",
    },
}


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _format_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    minutes, remainder = divmod(seconds, 60.0)
    hours, minutes = divmod(int(minutes), 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{remainder:05.2f}"
    return f"{minutes:02d}:{remainder:05.2f}"


class DesktopApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.preferences = _load_json(PREFERENCES_PATH)
        self.language = self.preferences.get("ui_language", "en")
        if self.language not in TEXT:
            self.language = "en"
        self.config = _load_json(CONFIG_PATH)
        self.backend = str(self.config.get("backend", "cpu")).casefold()
        self.media_path: Path | None = None
        self.duration = 0.0
        self.peaks: list[float] = []
        self.range_start = 0.0
        self.range_end = 0.0
        self.drag_start_x: float | None = None
        self.worker: threading.Thread | None = None
        self.cancel_event = threading.Event()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.last_output: Path | None = None

        root.title(APP_NAME)
        root.geometry("860x720")
        root.minsize(720, 620)
        self._configure_style()
        self._build()
        self._apply_language()
        root.after(100, self._poll_events)

    def tr(self, key: str) -> str:
        return TEXT[self.language][key]

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Hint.TLabel", foreground="#666666")
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8))

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill=BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=X, pady=(0, 10))
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(side=LEFT)
        self.language_box = ttk.Combobox(header, state="readonly", width=12, values=["English", "한국어"])
        self.language_box.pack(side=RIGHT)
        self.language_box.current(0 if self.language == "en" else 1)
        self.language_box.bind("<<ComboboxSelected>>", self._language_changed)

        self.media_label = ttk.Label(outer, style="Section.TLabel")
        self.media_label.pack(anchor="w")
        self.media_hint = ttk.Label(outer, style="Hint.TLabel", wraplength=900)
        self.media_hint.pack(anchor="w", pady=(2, 6))
        media_row = ttk.Frame(outer)
        media_row.pack(fill=X)
        self.media_name = ttk.Label(media_row, relief="sunken", padding=8)
        self.media_name.pack(side=LEFT, fill=X, expand=True)
        self.browse_button = ttk.Button(media_row, command=self._browse_media)
        self.browse_button.pack(side=RIGHT, padx=(8, 0))

        self.range_label = ttk.Label(outer, style="Section.TLabel")
        self.range_label.pack(anchor="w", pady=(14, 0))
        range_modes = ttk.Frame(outer)
        range_modes.pack(fill=X, pady=(3, 4))
        self.range_mode = StringVar(value="full")
        self.full_radio = ttk.Radiobutton(range_modes, variable=self.range_mode, value="full", command=self._range_mode_changed)
        self.full_radio.pack(side=LEFT)
        self.selection_radio = ttk.Radiobutton(range_modes, variable=self.range_mode, value="selection", command=self._range_mode_changed)
        self.selection_radio.pack(side=LEFT, padx=(20, 0))
        self.range_readout = ttk.Label(range_modes, text="00:00.00 — 00:00.00")
        self.range_readout.pack(side=RIGHT)
        self.waveform = Canvas(outer, height=88, background="#20242b", highlightthickness=1, highlightbackground="#555b66")
        self.waveform.pack(fill=X)
        self.waveform.bind("<Button-1>", self._wave_press)
        self.waveform.bind("<B1-Motion>", self._wave_drag)
        self.waveform.bind("<ButtonRelease-1>", self._wave_release)
        self.waveform.bind("<Configure>", lambda _event: self._draw_waveform())
        self.range_hint = ttk.Label(outer, style="Hint.TLabel", wraplength=900)
        self.range_hint.pack(anchor="w", pady=(4, 0))

        self.lyrics_label = ttk.Label(outer, style="Section.TLabel")
        self.lyrics_label.pack(anchor="w", pady=(14, 0))
        self.lyrics_hint = ttk.Label(outer, style="Hint.TLabel", wraplength=900)
        self.lyrics_hint.pack(anchor="w", pady=(2, 4))
        self.lyrics = Text(outer, height=7, wrap="word", undo=True, font=("Segoe UI", 10))
        self.lyrics.pack(fill=BOTH, expand=True)
        self.load_button = ttk.Button(outer, command=self._load_lyrics)
        self.load_button.pack(anchor="e", pady=(5, 0))

        options = ttk.Frame(outer)
        options.pack(fill=X, pady=(12, 0))
        self.mode_label = ttk.Label(options, style="Section.TLabel")
        self.mode_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.mode_box = ttk.Combobox(options, state="readonly", width=25)
        self.mode_box.grid(row=0, column=1, sticky="ew")
        self.mode_box.bind("<<ComboboxSelected>>", lambda _event: self._update_manual_visibility())
        self.device_label = ttk.Label(options)
        self.device_label.grid(row=0, column=2, sticky="e", padx=(24, 8))
        devices = (
            ["CUDA · NVIDIA", "CPU"]
            if self.backend == "cuda"
            else ["Apple GPU · Metal", "CPU"]
            if self.backend == "mps"
            else ["CPU"]
        )
        self.device_box = ttk.Combobox(options, state="readonly", width=20, values=devices)
        self.device_box.grid(row=0, column=3, sticky="ew")
        self.device_box.current(0)
        options.columnconfigure(1, weight=1)
        options.columnconfigure(3, weight=1)

        self.manual_frame = ttk.Frame(outer)
        ttk.Label(self.manual_frame, text="").grid(row=0, column=0)
        self.max_chars_label = ttk.Label(self.manual_frame)
        self.max_chars_label.grid(row=0, column=1, padx=(0, 5))
        self.max_chars = StringVar(value="30")
        ttk.Spinbox(self.manual_frame, from_=1, to=80, width=6, textvariable=self.max_chars).grid(row=0, column=2)
        self.max_duration_label = ttk.Label(self.manual_frame)
        self.max_duration_label.grid(row=0, column=3, padx=(18, 5))
        self.max_duration = StringVar(value="10")
        ttk.Spinbox(self.manual_frame, from_=3, to=30, width=6, textvariable=self.max_duration).grid(row=0, column=4)
        self.end_hold_label = ttk.Label(self.manual_frame)
        self.end_hold_label.grid(row=0, column=5, padx=(18, 5))
        self.end_hold = ttk.Combobox(self.manual_frame, state="readonly", width=10, values=["0.3 s", "0.5 s", "1.0 s", "1.5 s"])
        self.end_hold.grid(row=0, column=6)
        self.end_hold.current(1)

        self.guide = ttk.Label(outer, style="Hint.TLabel", wraplength=900)
        self.guide.pack(fill=X, pady=(10, 6))
        action_row = ttk.Frame(outer)
        action_row.pack(fill=X)
        self.status = ttk.Label(action_row)
        self.status.pack(side=LEFT, fill=X, expand=True)
        self.open_folder_button = ttk.Button(action_row, command=self._open_output_folder)
        self.cancel_button = ttk.Button(action_row, command=self._cancel)
        self.generate_button = ttk.Button(action_row, style="Primary.TButton", command=self._generate)
        self.generate_button.pack(side=RIGHT)
        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill=X, pady=(7, 0))
        self.log = Text(outer, height=4, state="disabled", wrap="word", font=("Consolas", 9))
        self.log.pack(fill=X, pady=(6, 0))

    def _apply_language(self) -> None:
        self.media_label.configure(text=self.tr("media"))
        self.media_hint.configure(text=self.tr("drop"))
        self.browse_button.configure(text=self.tr("browse"))
        if self.media_path is None:
            self.media_name.configure(text=self.tr("no_media"))
        self.range_label.configure(text=self.tr("range"))
        self.full_radio.configure(text=self.tr("full"))
        self.selection_radio.configure(text=self.tr("selection"))
        self.range_hint.configure(text=self.tr("range_help"))
        self.lyrics_label.configure(text=self.tr("lyrics"))
        self.lyrics_hint.configure(text=self.tr("lyrics_hint"))
        self.load_button.configure(text=self.tr("load"))
        self.mode_label.configure(text=self.tr("mode"))
        current_mode = self.mode_box.current()
        self.mode_box.configure(values=[self.tr("auto"), self.tr("manual")])
        self.mode_box.current(max(0, current_mode))
        self.device_label.configure(text=self.tr("device"))
        self.max_chars_label.configure(text=self.tr("max_chars"))
        self.max_duration_label.configure(text=self.tr("max_duration"))
        self.end_hold_label.configure(text=self.tr("end_hold"))
        self.guide.configure(text=self.tr("guide"))
        self.generate_button.configure(text=self.tr("generate"))
        self.cancel_button.configure(text=self.tr("cancel"))
        self.open_folder_button.configure(text=self.tr("open_folder"))
        if not self.worker or not self.worker.is_alive():
            self.status.configure(text=self.tr("ready"))

    def _language_changed(self, _event=None) -> None:
        self.language = "en" if self.language_box.current() == 0 else "ko"
        PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)
        PREFERENCES_PATH.write_text(json.dumps({"ui_language": self.language}), encoding="utf-8")
        self._apply_language()

    def _browse_media(self) -> None:
        selected = filedialog.askopenfilename(
            title=self.tr("browse"),
            filetypes=[
                ("Media", "*.mp4 *.mov *.mkv *.avi *.m4a *.aac *.mp3 *.wav *.flac *.ogg *.opus *.webm"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self._load_media(Path(selected))

    def _load_media(self, path: Path) -> None:
        self.media_path = path
        self.media_name.configure(text=path.name)
        self.status.configure(text=self.tr("loading"))
        self.peaks = []
        self._draw_waveform()
        threading.Thread(target=self._waveform_worker, args=(path,), daemon=True).start()

    def _waveform_worker(self, path: Path) -> None:
        try:
            duration, peaks = waveform_peaks(path, bins=900)
            self.events.put(("waveform", (path, duration, peaks)))
        except Exception as exc:
            self.events.put(("media_error", (path, str(exc))))

    def _range_mode_changed(self) -> None:
        if self.range_mode.get() == "full":
            self.range_start = 0.0
            self.range_end = self.duration
        self._update_range_readout()
        self._draw_waveform()

    def _wave_press(self, event) -> None:
        if self.duration <= 0:
            return
        self.range_mode.set("selection")
        self.drag_start_x = float(event.x)
        position = self._x_to_time(event.x)
        self.range_start = position
        self.range_end = position
        self._draw_waveform()

    def _wave_drag(self, event) -> None:
        if self.drag_start_x is None or self.duration <= 0:
            return
        first = self._x_to_time(self.drag_start_x)
        second = self._x_to_time(event.x)
        self.range_start, self.range_end = sorted((first, second))
        self._update_range_readout()
        self._draw_waveform()

    def _wave_release(self, event) -> None:
        self._wave_drag(event)
        self.drag_start_x = None

    def _x_to_time(self, x: float) -> float:
        width = max(1, self.waveform.winfo_width())
        return max(0.0, min(self.duration, float(x) / width * self.duration))

    def _draw_waveform(self) -> None:
        canvas = self.waveform
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        middle = height / 2
        if self.peaks:
            step = width / len(self.peaks)
            for index, peak in enumerate(self.peaks):
                x = index * step
                amplitude = max(1.0, peak * (height * 0.44))
                canvas.create_line(x, middle - amplitude, x, middle + amplitude, fill="#79d8a5")
        if self.duration > 0 and self.range_mode.get() == "selection":
            left = self.range_start / self.duration * width
            right = self.range_end / self.duration * width
            canvas.create_rectangle(0, 0, left, height, fill="#101318", stipple="gray50", outline="")
            canvas.create_rectangle(right, 0, width, height, fill="#101318", stipple="gray50", outline="")
            canvas.create_line(left, 0, left, height, fill="#ffd166", width=2)
            canvas.create_line(right, 0, right, height, fill="#ffd166", width=2)

    def _update_range_readout(self) -> None:
        end = self.duration if self.range_mode.get() == "full" else self.range_end
        start = 0.0 if self.range_mode.get() == "full" else self.range_start
        self.range_readout.configure(text=f"{_format_time(start)} — {_format_time(end)}")

    def _load_lyrics(self) -> None:
        selected = filedialog.askopenfilename(title=self.tr("load"), filetypes=[("Text", "*.txt"), ("All files", "*.*")])
        if selected:
            text = Path(selected).read_text(encoding="utf-8-sig")
            self.lyrics.delete("1.0", END)
            self.lyrics.insert("1.0", text)

    def _update_manual_visibility(self) -> None:
        if self.mode_box.current() == 1:
            self.manual_frame.pack(fill=X, pady=(8, 0), before=self.guide)
        else:
            self.manual_frame.pack_forget()

    def _selected_device(self) -> str:
        if self.backend in {"cuda", "mps"} and self.device_box.current() == 0:
            return self.backend
        return "cpu"

    def _generate(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if self.media_path is None or not self.media_path.is_file():
            messagebox.showinfo(APP_NAME, self.tr("need_media"))
            return
        lyrics = self.lyrics.get("1.0", END).strip()
        if not lyrics:
            messagebox.showinfo(APP_NAME, self.tr("need_lyrics"))
            return
        selected = self.range_mode.get() == "selection"
        if selected and self.range_end - self.range_start < 1.0:
            messagebox.showinfo(APP_NAME, self.tr("bad_range"))
            return
        output_dir = Path.home() / "Documents" / APP_NAME
        output_dir.mkdir(parents=True, exist_ok=True)
        default_name = f"{self.media_path.stem}-{datetime.now():%Y%m%d-%H%M%S}.srt"
        output = filedialog.asksaveasfilename(
            title=self.tr("save_title"),
            initialdir=str(output_dir),
            initialfile=default_name,
            defaultextension=".srt",
            filetypes=[("SubRip subtitles", "*.srt")],
        )
        if not output:
            return

        handle, lyrics_name = tempfile.mkstemp(prefix="vilm-lyrics-", suffix=".txt")
        os.close(handle)
        lyrics_path = Path(lyrics_name)
        lyrics_path.write_text(lyrics, encoding="utf-8")
        self.cancel_event.clear()
        self.last_output = None
        self.generate_button.pack_forget()
        self.cancel_button.pack(side=RIGHT)
        self.open_folder_button.pack_forget()
        self.progress.start(12)
        self.status.configure(text=self.tr("processing"))
        self._set_log("")
        options = {
            "max_chars": self.max_chars.get(),
            "max_duration": self.max_duration.get(),
            "end_hold_index": self.end_hold.current(),
            "automatic": self.mode_box.current() == 0,
            "device": self._selected_device(),
            "range_start": self.range_start,
            "range_end": self.range_end,
        }
        self.worker = threading.Thread(
            target=self._alignment_worker,
            args=(lyrics_path, Path(output), selected, options),
            daemon=True,
        )
        self.worker.start()

    def _alignment_worker(self, lyrics_path: Path, output: Path, selected: bool, options: dict) -> None:
        assert self.media_path is not None
        python = Path(sys.executable)
        if python.name.casefold() == "pythonw.exe":
            console_python = python.with_name("python.exe")
            if console_python.is_file():
                python = console_python
        command = [
            str(python), "-m", "lyrics_aligner", "align",
            str(self.media_path), str(lyrics_path), "-o", str(output),
            "--max-chars", str(options["max_chars"]),
            "--max-duration-ms", str(int(options["max_duration"]) * 1000),
            "--end-pad-ms", str([300, 500, 1000, 1500][int(options["end_hold_index"])]),
            "--min-gap-ms", "80",
            "--timeline-anchor",
        ]
        if options["automatic"]:
            command.append("--auto-segment")
        if selected:
            command.extend([
                "--range-start", f"{float(options['range_start']):.6f}",
                "--range-end", f"{float(options['range_end']):.6f}",
                "--partial-range",
            ])
        env = os.environ.copy()
        env["LYRICS_ALIGNER_DEVICE"] = str(options["device"])
        try:
            result = run_streaming_process(
                command,
                env=env,
                cancel_requested=self.cancel_event.is_set,
                on_output=lambda line: self.events.put(("log", line)),
            )
            if result.returncode != 0:
                raise RuntimeError(result.output.strip() or "Alignment failed")
            self.events.put(("complete", output))
        except JobCancelled:
            output.unlink(missing_ok=True)
            self.events.put(("cancelled", None))
        except Exception as exc:
            output.unlink(missing_ok=True)
            self.events.put(("failed", str(exc)))
        finally:
            lyrics_path.unlink(missing_ok=True)

    def _cancel(self) -> None:
        self.cancel_event.set()
        self.status.configure(text=f"{self.tr('cancelled')}…")

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "waveform":
                    path, duration, peaks = payload
                    if self.media_path == path:
                        self.duration = float(duration)
                        self.peaks = list(peaks)
                        self.range_start = 0.0
                        self.range_end = self.duration
                        self.range_mode.set("full")
                        self._update_range_readout()
                        self._draw_waveform()
                        self.status.configure(text=self.tr("ready"))
                elif kind == "media_error":
                    path, error = payload
                    if self.media_path == path:
                        self.media_path = None
                        self.media_name.configure(text=self.tr("no_media"))
                        self.status.configure(text=self.tr("ready"))
                        messagebox.showerror(self.tr("file_error"), error)
                elif kind == "log":
                    self._append_log(str(payload))
                elif kind == "complete":
                    self.last_output = Path(payload)
                    self.status.configure(text=f"{self.tr('done')}  {self.last_output}")
                    self._finish_job(show_folder=True)
                elif kind == "cancelled":
                    self.status.configure(text=self.tr("cancelled"))
                    self._finish_job()
                elif kind == "failed":
                    self.status.configure(text=self.tr("failed"))
                    self._finish_job()
                    messagebox.showerror(self.tr("failed"), str(payload))
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _finish_job(self, show_folder: bool = False) -> None:
        self.progress.stop()
        self.cancel_button.pack_forget()
        if show_folder:
            self.open_folder_button.pack(side=RIGHT, padx=(0, 8))
        self.generate_button.pack(side=RIGHT)

    def _set_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", END)
        if text:
            self.log.insert(END, text)
        self.log.configure(state="disabled")

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert(END, text + "\n")
        self.log.see(END)
        self.log.configure(state="disabled")

    def _open_output_folder(self) -> None:
        if self.last_output is None:
            return
        folder = str(self.last_output.parent)
        if os.name == "nt":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])


def main() -> int:
    root = Tk()
    DesktopApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
