"""Known-lyrics alignment and SRT generation."""

from __future__ import annotations

import os
import sys

from .platform_paths import managed_runtime_root
from .windows_install import register_windows_uninstaller


__version__ = "1.0.0"


def _configure_managed_install() -> None:
    """Keep model files removable and register Windows uninstall metadata."""
    runtime_root = managed_runtime_root()
    if runtime_root is None:
        return
    model_root = runtime_root / "models"
    os.environ.setdefault("XDG_CACHE_HOME", str(model_root))
    os.environ.setdefault("TORCH_HOME", str(model_root / "torch"))
    if sys.platform == "darwin":
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    register_windows_uninstaller()


_configure_managed_install()
