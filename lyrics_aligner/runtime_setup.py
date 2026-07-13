from __future__ import annotations

import json
from dataclasses import asdict

from .device import choose_devices


def prepare_runtime(model_name: str = "small") -> dict:
    """Download required models and verify the private application runtime."""
    import torch
    import stable_whisper
    from demucs.pretrained import get_model
    from stable_whisper.stabilization import load_silero_vad_model

    choice = choose_devices()
    print(f"[1/4] Preparing Whisper {model_name}…", flush=True)
    model_device = "mps" if choice.whisper == "mps" else "cpu"
    whisper_model = stable_whisper.load_model(model_name, device=model_device)
    del whisper_model

    print("[2/4] Preparing the Demucs vocal-separation model…", flush=True)
    separation_model = get_model("htdemucs")
    del separation_model

    print("[3/4] Preparing the voice-activity model…", flush=True)
    vad_model, _ = load_silero_vad_model(verbose=False)
    del vad_model

    print("[4/4] Checking the processing device…", flush=True)
    if choice.whisper == "cuda":
        probe = torch.ones(1, device="cuda") * 2
        if float(probe.cpu().item()) != 2.0:
            raise RuntimeError("CUDA self-check returned an invalid result")
    elif choice.whisper == "mps":
        probe = torch.ones(1, device="mps") * 2
        if float(probe.cpu().item()) != 2.0:
            raise RuntimeError("MPS self-check returned an invalid result")
    else:
        probe = torch.ones(1) * 2
        if float(probe.item()) != 2.0:
            raise RuntimeError("CPU self-check returned an invalid result")

    result = {
        "ok": True,
        "model": model_name,
        "torch": torch.__version__,
        "devices": asdict(choice),
    }
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main() -> int:
    try:
        prepare_runtime()
    except Exception as exc:
        print(f"Runtime setup failed: {exc}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
