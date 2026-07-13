import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile

from lyrics_aligner.cli import main


class WaveformCliTests(unittest.TestCase):
    def test_waveform_command_outputs_compact_json(self):
        with tempfile.TemporaryDirectory() as directory:
            media = Path(directory) / "audio.wav"
            soundfile.write(media, np.zeros(8000, dtype=np.float32), 8000)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["waveform", str(media), "--bins", "32"])
            payload = json.loads(output.getvalue())
            self.assertEqual(result, 0)
            self.assertAlmostEqual(payload["duration"], 1.0, places=2)
            self.assertEqual(len(payload["peaks"]), 32)


if __name__ == "__main__":
    unittest.main()
