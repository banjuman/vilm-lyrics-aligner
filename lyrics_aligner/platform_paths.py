from __future__ import annotations

import os
import sys
from pathlib import Path


def application_data_root() -> Path:
    """Return the private per-user data directory used by the desktop app."""
    override = os.environ.get("LYRICS_ALIGNER_APP_ROOT")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Vilm Lyrics Aligner"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LyricsAligner"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "Vilm Lyrics Aligner"


def managed_runtime_root() -> Path | None:
    """Identify a one-click managed install without mistaking a source checkout."""
    project_root = Path(__file__).resolve().parent.parent
    if project_root.name.casefold() != "app":
        return None
    runtime_root = project_root.parent
    expected = application_data_root()
    try:
        return runtime_root if runtime_root.resolve() == expected.resolve() else None
    except OSError:
        return None
