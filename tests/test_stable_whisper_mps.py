import unittest

from lyrics_aligner.backends.stable_whisper import _make_mps_safe_dtw


class _Device:
    def __init__(self, kind):
        self.type = kind


class _FakeTensor:
    def __init__(self, device, events):
        self.device = _Device(device)
        self.events = events

    def cpu(self):
        self.events.append("cpu")
        self.device = _Device("cpu")
        return self

    def double(self):
        self.events.append("double")
        return self

    def numpy(self):
        self.events.append("numpy")
        return "array"


class MpsWhisperCompatibilityTests(unittest.TestCase):
    def test_mps_moves_to_cpu_before_requesting_float64(self):
        events = []

        def original(_costs):
            events.append("original")

        def cpu(array):
            events.append(("dtw_cpu", array))
            return "path"

        patched = _make_mps_safe_dtw(original, cpu)
        result = patched(_FakeTensor("mps", events))

        self.assertEqual(result, "path")
        self.assertEqual(
            events,
            ["cpu", "double", "numpy", ("dtw_cpu", "array")],
        )

    def test_non_mps_uses_the_upstream_implementation(self):
        calls = []

        def original(costs):
            calls.append(costs)
            return "original path"

        patched = _make_mps_safe_dtw(original, lambda _array: None)
        tensor = _FakeTensor("cpu", [])

        self.assertEqual(patched(tensor), "original path")
        self.assertEqual(calls, [tensor])


if __name__ == "__main__":
    unittest.main()
