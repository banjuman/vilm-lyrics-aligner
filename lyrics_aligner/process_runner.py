from __future__ import annotations

import os
import queue
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


class JobCancelled(RuntimeError):
    pass


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    output: str


def run_streaming_process(
    command: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    cancel_requested: Callable[[], bool] | None = None,
    on_output: Callable[[str], None] | None = None,
    poll_interval: float = 0.1,
) -> ProcessResult:
    """Run a child process while streaming merged UTF-8 output and supporting cancel."""
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    popen_options = {}
    if os.name == "nt":
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_options["start_new_session"] = True
    child_env = os.environ.copy()
    if env is not None:
        child_env.update(env)
    child_env.setdefault("PYTHONUTF8", "1")
    child_env.setdefault("PYTHONIOENCODING", "utf-8")
    process = subprocess.Popen(
        list(command),
        cwd=str(cwd) if cwd is not None else None,
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=creationflags,
        **popen_options,
    )
    output_queue: queue.Queue[str | None] = queue.Queue()

    def read_output() -> None:
        assert process.stdout is not None
        try:
            for line in process.stdout:
                output_queue.put(line)
        finally:
            output_queue.put(None)

    reader = threading.Thread(target=read_output, name="lyrics-aligner-output", daemon=True)
    reader.start()
    collected: list[str] = []
    reader_done = False

    try:
        while process.poll() is None or not reader_done:
            if cancel_requested is not None and cancel_requested():
                _terminate_process_tree(process)
                raise JobCancelled("Job cancelled")
            try:
                item = output_queue.get(timeout=poll_interval)
            except queue.Empty:
                continue
            if item is None:
                reader_done = True
                continue
            collected.append(item)
            if on_output is not None:
                on_output(item.rstrip("\r\n"))
        return ProcessResult(returncode=int(process.returncode or 0), output="".join(collected))
    finally:
        if process.poll() is None:
            _terminate_process_tree(process)
        reader.join(timeout=0.5)
        # Closing a pipe while another thread is blocked in read() can itself
        # block on Windows. The daemon reader owns it until the process tree is
        # gone, so only close synchronously once the reader has finished.
        if process.stdout is not None and not reader.is_alive():
            process.stdout.close()


def _terminate_process_tree(process: subprocess.Popen) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
    try:
        process.wait(timeout=1)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
    try:
        process.kill()
        process.wait(timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        pass
