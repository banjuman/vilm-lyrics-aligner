import tempfile
import unittest
from pathlib import Path


class DemucsSoundFileIoTests(unittest.TestCase):
    def test_load_track_does_not_require_torchcodec(self):
        import numpy as np
        import soundfile
        import demucs.separate as demucs_separate

        from lyrics_aligner.backends.demucs import _install_soundfile_io

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.wav"
            soundfile.write(path, np.zeros((8000, 1), dtype="float32"), 16000)
            _install_soundfile_io()
            wav = demucs_separate.load_track(path, 2, 16000)
        self.assertEqual(tuple(wav.shape), (2, 8000))


if __name__ == "__main__":
    unittest.main()
