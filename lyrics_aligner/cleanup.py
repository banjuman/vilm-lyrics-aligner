from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path


def cleanup_stale_workdirs(
    *,
    temp_root: str | Path | None = None,
    max_age_seconds: float = 24 * 60 * 60,
    now: float | None = None,
) -> int:
    """Remove only old Lyrics Aligner work directories from the OS temp root."""
    root = Path(temp_root or tempfile.gettempdir()).resolve()
    current_time = time.time() if now is None else float(now)
    removed = 0
    for path in root.glob("lyrics-aligner-*"):
        try:
            resolved = path.resolve()
            if (
                not path.is_dir()
                or path.is_symlink()
                or resolved.parent != root
                or current_time - path.stat().st_mtime < max_age_seconds
            ):
                continue
            shutil.rmtree(resolved)
            removed += 1
        except OSError:
            continue
    return removed


def cleanup_old_diagnostics(
    directory: str | Path,
    *,
    max_age_seconds: float = 30 * 24 * 60 * 60,
    now: float | None = None,
) -> int:
    """Remove old JSON diagnostics without touching other files."""
    root = Path(directory)
    if not root.is_dir():
        return 0
    current_time = time.time() if now is None else float(now)
    removed = 0
    for path in root.glob("*.json"):
        try:
            if (
                not path.is_file()
                or path.is_symlink()
                or path.resolve().parent != root.resolve()
                or current_time - path.stat().st_mtime < max_age_seconds
            ):
                continue
            path.unlink()
            removed += 1
        except OSError:
            continue
    return removed
