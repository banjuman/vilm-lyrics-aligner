import unittest
from unittest.mock import patch

from lyrics_aligner.device import choose_devices


class DeviceSelectionTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    @patch("torch.cuda.get_device_name", return_value="Test NVIDIA")
    @patch("torch.cuda.is_available", return_value=True)
    def test_prefers_cuda_when_available(self, _available, _name):
        choice = choose_devices()
        self.assertEqual((choice.whisper, choice.separation), ("cuda", "cuda"))

    @patch.dict("os.environ", {}, clear=True)
    @patch("platform.system", return_value="Windows")
    @patch("torch.cuda.is_available", return_value=False)
    def test_windows_without_nvidia_falls_back_to_cpu(self, _available, _system):
        choice = choose_devices()
        self.assertEqual((choice.whisper, choice.separation), ("cpu", "cpu"))

    @patch.dict("os.environ", {}, clear=True)
    @patch("platform.system", return_value="Darwin")
    @patch("torch.backends.mps.is_available", return_value=True)
    @patch("torch.cuda.is_available", return_value=False)
    def test_apple_silicon_uses_metal_for_whisper_and_cpu_for_demucs(
        self, _cuda, _mps, _system
    ):
        choice = choose_devices()
        self.assertEqual((choice.whisper, choice.separation), ("mps", "cpu"))
    @patch.dict("os.environ", {"LYRICS_ALIGNER_DEVICE": "cpu"}, clear=True)
    def test_support_override_is_not_a_user_facing_choice(self):
        choice = choose_devices()
        self.assertEqual((choice.whisper, choice.separation), ("cpu", "cpu"))


if __name__ == "__main__":
    unittest.main()
