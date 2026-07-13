import os
import time
from pathlib import Path

import librosa
import stable_whisper

audio_path = Path(os.environ["TEMP"]) / "lyrics-aligner-smoke.wav"
audio, _ = librosa.load(audio_path, sr=16000, mono=True)
text = "Hello, this is a timing test.\nWe already know every word.\nPlease align this text to the audio."

started = time.perf_counter()
model = stable_whisper.load_model("small", device="cuda")
print(f"model {time.perf_counter() - started:.2f}s", flush=True)
started = time.perf_counter()
result = model.align(
    audio,
    text,
    language="en",
    original_split=True,
    fast_mode=True,
    failure_threshold=0.5,
)
print(f"align {time.perf_counter() - started:.2f}s", flush=True)
for segment in result.segments:
    print(segment.start, segment.end, segment.text, flush=True)
    for word in segment.words:
        print(" ", word.start, word.end, repr(word.word), flush=True)
