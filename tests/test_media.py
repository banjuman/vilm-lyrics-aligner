import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile

from lyrics_aligner.media import extract_audio_range, media_duration, waveform_peaks


class MediaTests(unittest.TestCase):
    def test_waveform_and_range_keep_source_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.wav"
            output = root / "range.wav"
            rate = 8000
            time = np.arange(rate * 3, dtype=np.float32) / rate
            audio = 0.4 * np.sin(2 * math.pi * 220 * time)
            soundfile.write(source, audio, rate)

            self.assertAlmostEqual(media_duration(source), 3.0, places=2)
            duration, peaks = waveform_peaks(source, bins=80)
            self.assertAlmostEqual(duration, 3.0, places=2)
            self.assertEqual(len(peaks), 80)
            self.assertGreater(max(peaks), 0.8)

            extract_audio_range(source, output, 0.75, 2.25, sample_rate=rate)
            self.assertAlmostEqual(media_duration(output), 1.5, places=2)

    def test_rejects_empty_range(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.wav"
            soundfile.write(path, np.zeros(8000, dtype=np.float32), 8000)
            with self.assertRaisesRegex(ValueError, "positive duration"):
                extract_audio_range(path, Path(directory) / "out.wav", 0.8, 0.2)


    def test_float_wav_duration_is_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "float-source.wav"
            soundfile.write(
                path,
                np.zeros(12000, dtype=np.float32),
                8000,
                subtype="FLOAT",
            )
            self.assertAlmostEqual(media_duration(path), 1.5, places=3)


if __name__ == "__main__":
    unittest.main()
