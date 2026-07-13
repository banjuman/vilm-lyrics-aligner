import tempfile
import unittest

from lyrics_aligner.resolve_bridge import render_timeline_audio
from test_resolve_bridge import FakeProject, FakeTimeline


class EmptyWaveCodecProject(FakeProject):
    def GetRenderCodecs(self, render_format):
        return {}

    def SetCurrentRenderFormatAndCodec(self, render_format, codec):
        self.render_format = (render_format, codec)
        return render_format == "wav" and codec == "LinearPCM"


class ResolveWaveFallbackTests(unittest.TestCase):
    def test_uses_linear_pcm_when_resolve_returns_empty_wave_codec_map(self):
        project = EmptyWaveCodecProject()
        with tempfile.TemporaryDirectory() as directory:
            output, _ = render_timeline_audio(project, FakeTimeline(), directory)
            self.assertTrue(output.exists())
        self.assertEqual(project.render_format, ("wav", "LinearPCM"))


if __name__ == "__main__":
    unittest.main()
