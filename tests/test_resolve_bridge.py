import tempfile
import unittest
from pathlib import Path

from lyrics_aligner.resolve_bridge import (
    choose_timeline_range,
    import_srt_to_timeline,
    render_timeline_audio,
    timeline_frame_rate,
)


class FakeTimeline:
    def __init__(self, marks=None):
        self.marks = marks or {}
        self.subtitle_tracks = 0

    def GetMarkInOut(self):
        return self.marks

    def ClearMarkInOut(self, kind="all"):
        self.marks = {}
        return True

    def SetMarkInOut(self, mark_in, mark_out, kind="all"):
        selected = {"in": mark_in, "out": mark_out}
        if kind == "all":
            self.marks = {"video": dict(selected), "audio": dict(selected)}
        else:
            self.marks[kind] = selected
        return True

    def GetStartFrame(self):
        return 100

    def GetEndFrame(self):
        return 999

    def GetTrackCount(self, kind):
        return self.subtitle_tracks if kind == "subtitle" else 0

    def AddTrack(self, kind):
        if kind == "subtitle":
            self.subtitle_tracks += 1
        return True


class FakeMediaPool:
    def __init__(self):
        self.append_info = None

    def ImportMedia(self, paths):
        return [{"path": paths[0]}]

    def AppendToTimeline(self, info):
        self.append_info = info
        return [object()]


class FakeProject:
    def __init__(self, media_pool=None):
        self.settings = None
        self.job = None
        self.restored = False
        self.deleted_preset = False
        self.deleted_job = False
        self.media_pool = media_pool or FakeMediaPool()

    def GetCurrentRenderFormatAndCodec(self):
        return {"format": "mov", "codec": "H264"}

    def GetCurrentRenderMode(self):
        return 0

    def SaveAsNewRenderPreset(self, name):
        self.preset = name
        return True

    def GetRenderFormats(self):
        return {"Wave": "wav"}

    def GetRenderCodecs(self, render_format):
        return {"Linear PCM": "LinearPCM"}

    def SetCurrentRenderFormatAndCodec(self, render_format, codec):
        self.render_format = (render_format, codec)
        return True

    def SetCurrentRenderMode(self, mode):
        self.render_mode = mode
        return True

    def SetRenderSettings(self, settings):
        self.settings = settings
        return True

    def AddRenderJob(self):
        self.job = "job-1"
        return self.job

    def StartRendering(self, jobs, interactive):
        output = Path(self.settings["TargetDir"]) / f'{self.settings["CustomName"]}.wav'
        output.touch()
        return jobs == [self.job]

    def IsRenderingInProgress(self):
        return False

    def GetRenderJobStatus(self, job_id):
        return {"JobStatus": "Complete", "CompletionPercentage": 100}

    def DeleteRenderJob(self, job_id):
        self.deleted_job = True
        return True

    def LoadRenderPreset(self, name):
        self.restored = name == self.preset
        if getattr(self, "mark_timeline", None) is not None:
            self.mark_timeline.marks = {}
        return self.restored

    def DeleteRenderPreset(self, name):
        self.deleted_preset = name == self.preset
        return self.deleted_preset

    def GetSetting(self, name):
        return "24" if name == "timelineFrameRate" else None

    def GetMediaPool(self):
        return self.media_pool


class ResolveBridgeTests(unittest.TestCase):
    def test_marked_range_preferred(self):
        timeline = FakeTimeline({"audio": {"in": 240, "out": 480}})
        selected = choose_timeline_range(timeline, True)
        self.assertEqual((selected.start_frame, selected.end_frame), (340, 580))
        self.assertTrue(selected.used_marks)

    def test_stale_full_range_mark_is_not_duplicated(self):
        timeline = FakeTimeline({
            "video": {"in": 0, "out": 899},
            "audio": {"in": 140, "out": 380},
        })
        project = FakeProject()
        with tempfile.TemporaryDirectory() as directory:
            render_timeline_audio(project, timeline, directory, use_marks=True)
        self.assertEqual(timeline.marks, {"audio": {"in": 140, "out": 380}})

    def test_render_preserves_timeline_in_out_marks(self):
        marks = {
            "video": {"in": 210, "out": 420},
            "audio": {"in": 220, "out": 410},
        }
        timeline = FakeTimeline(marks)
        project = FakeProject()
        project.mark_timeline = timeline
        with tempfile.TemporaryDirectory() as directory:
            render_timeline_audio(project, timeline, directory, use_marks=True)
        self.assertEqual(timeline.marks, marks)

    def test_render_converts_relative_marks_to_absolute_deliver_frames(self):
        project = FakeProject()
        timeline = FakeTimeline({"audio": {"in": 240, "out": 480}})
        with tempfile.TemporaryDirectory() as directory:
            _, selected = render_timeline_audio(project, timeline, directory, use_marks=True)
        self.assertEqual((selected.start_frame, selected.end_frame), (340, 580))
        self.assertEqual((project.settings["MarkIn"], project.settings["MarkOut"]), (340, 580))

    def test_render_restores_deliver_preset_and_deletes_own_job(self):
        project = FakeProject()
        timeline = FakeTimeline()
        with tempfile.TemporaryDirectory() as directory:
            output, selected = render_timeline_audio(project, timeline, directory)
            self.assertTrue(output.exists())
        self.assertEqual((selected.start_frame, selected.end_frame), (100, 999))
        self.assertEqual(project.settings["ExportVideo"], False)
        self.assertEqual(project.settings["ExportAudio"], True)
        self.assertTrue(project.restored)
        self.assertTrue(project.deleted_preset)
        self.assertTrue(project.deleted_job)

    def test_reads_project_timeline_frame_rate(self):
        self.assertEqual(timeline_frame_rate(FakeProject(), FakeTimeline()), 24.0)

    def test_imports_srt_at_requested_frame(self):
        media_pool = FakeMediaPool()
        project = FakeProject(media_pool)
        timeline = FakeTimeline()
        with tempfile.TemporaryDirectory() as directory:
            srt = Path(directory) / "test.srt"
            srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")
            result = import_srt_to_timeline(project, timeline, srt, 120)
        self.assertTrue(result)
        self.assertEqual(timeline.subtitle_tracks, 1)
        self.assertEqual(media_pool.append_info[0]["recordFrame"], 120)


if __name__ == "__main__":
    unittest.main()
