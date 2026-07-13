import tempfile
import unittest
from pathlib import Path

from lyrics_aligner.resolve_bridge import render_timeline_audio
from test_resolve_bridge import FakeProject, FakeTimeline


class AacCapableProject(FakeProject):
    def GetRenderFormats(self):
        return {"Wave": "wav", "MP4": "mp4", "QuickTime": "mov"}

    def GetRenderCodecs(self, render_format):
        if render_format in {"mp4", "MP4", "mov", "QuickTime"}:
            return {"H.264": "H264"}
        return {}

    def SetCurrentRenderFormatAndCodec(self, render_format, codec):
        self.render_format = (render_format, codec)
        return render_format in {"mp4", "mov"} and codec == "H264"

    def StartRendering(self, jobs, interactive):
        extension = "mp4" if self.render_format[0] == "mp4" else "mov"
        output = Path(self.settings["TargetDir"]) / f'{self.settings["CustomName"]}.{extension}'
        output.touch()
        return jobs == [self.job]


class RejectsAudioOnlyMp4Project(AacCapableProject):
    def StartRendering(self, *args):
        if not self.settings.get("ExportVideo"):
            return False
        output = Path(self.settings["TargetDir"]) / f'{self.settings["CustomName"]}.mov'
        output.touch()
        return args == ([self.job], False)

    def GetRenderJobList(self):
        return [{"JobId": self.job}]


class ResolveAacFallbackTests(unittest.TestCase):
    def test_skips_unreliable_audio_only_mp4_even_when_advertised(self):
        project = AacCapableProject()
        with tempfile.TemporaryDirectory() as directory:
            output, _ = render_timeline_audio(project, FakeTimeline(), directory)
            self.assertEqual(output.suffix, ".mov")
        self.assertTrue(project.settings["ExportVideo"])
        self.assertTrue(project.settings["ExportAudio"])

    def test_falls_back_to_video_mov_when_audio_only_mp4_will_not_start(self):
        project = RejectsAudioOnlyMp4Project()
        with tempfile.TemporaryDirectory() as directory:
            output, _ = render_timeline_audio(project, FakeTimeline(), directory)
            self.assertEqual(output.suffix, ".mov")
        self.assertTrue(project.settings["ExportVideo"])
        self.assertTrue(project.deleted_job)


if __name__ == "__main__":
    unittest.main()
