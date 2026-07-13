import tempfile
import unittest
from pathlib import Path

from lyrics_aligner.resolve_bridge import render_timeline_audio
from test_resolve_bridge import FakeProject, FakeTimeline


class QuickTimeFallbackProject(FakeProject):
    def GetRenderFormats(self):
        return {"Wave": "wav", "QuickTime": "mov"}

    def GetRenderCodecs(self, render_format):
        if render_format in {"mov", "QuickTime"}:
            return {"H.264": "H264"}
        return {}

    def SetCurrentRenderFormatAndCodec(self, render_format, codec):
        self.render_format = (render_format, codec)
        return render_format == "mov" and codec == "H264"

    def StartRendering(self, jobs, interactive):
        output = Path(self.settings["TargetDir"]) / f'{self.settings["CustomName"]}.mov'
        output.touch()
        return jobs == [self.job]


class ResolveQuickTimeFallbackTests(unittest.TestCase):
    def test_keeps_video_enabled_for_quicktime_job(self):
        project = QuickTimeFallbackProject()
        with tempfile.TemporaryDirectory() as directory:
            output, _ = render_timeline_audio(project, FakeTimeline(), directory)
            self.assertEqual(output.suffix, ".mov")
        self.assertEqual(project.render_format, ("mov", "H264"))
        self.assertEqual(project.settings["SelectAllFrames"], True)
        self.assertEqual(project.settings["ExportVideo"], True)
        self.assertEqual(project.settings["ExportAudio"], True)
        self.assertNotIn("AudioCodec", project.settings)


if __name__ == "__main__":
    unittest.main()
