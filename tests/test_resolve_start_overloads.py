import tempfile
import unittest
from pathlib import Path

from lyrics_aligner.resolve_bridge import render_timeline_audio
from test_resolve_bridge import FakeProject, FakeTimeline


class VariadicStartProject(FakeProject):
    def StartRendering(self, *job_ids):
        if job_ids != (self.job,):
            return False
        output = Path(self.settings["TargetDir"]) / f'{self.settings["CustomName"]}.wav'
        output.touch()
        return True


class ResolveStartOverloadTests(unittest.TestCase):
    def test_supports_variadic_single_job_overload(self):
        project = VariadicStartProject()
        with tempfile.TemporaryDirectory() as directory:
            output, _ = render_timeline_audio(project, FakeTimeline(), directory)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
