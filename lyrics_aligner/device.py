from __future__ import annotations

import os
import platform
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceChoice:
    whisper: str
    separation: str
    reason: str


def choose_devices() -> DeviceChoice:
    """Choose acceleration without exposing hardware choices to end users."""
    forced = os.environ.get("LYRICS_ALIGNER_DEVICE", "").strip().casefold()
    if forced in {"cuda", "cpu", "mps"}:
        separation = "cpu" if forced == "mps" else forced
        return DeviceChoice(forced, separation, f"forced by LYRICS_ALIGNER_DEVICE={forced}")

    try:
        import torch
    except ImportError:
        return DeviceChoice("cpu", "cpu", "PyTorch accelerator support unavailable")

    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        return DeviceChoice("cuda", "cuda", f"CUDA device detected: {name}")

    if platform.system() == "Darwin" and torch.backends.mps.is_available():
        # Whisper generally works through MPS. Demucs has unresolved complex-op
        # compatibility/performance variance, so CPU is the safe default.
        return DeviceChoice("mps", "cpu", "Apple Metal detected; Demucs uses safe CPU mode")

    return DeviceChoice("cpu", "cpu", "No supported GPU accelerator detected")
