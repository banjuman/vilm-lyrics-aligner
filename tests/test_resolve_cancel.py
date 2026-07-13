from __future__ import annotations

import unittest

from lyrics_aligner.resolve_bridge import RenderCancelled, _wait_for_render


class RenderingProject:
    def __init__(self) -> None:
        self.stopped = False

    def IsRenderingInProgress(self):
        return not self.stopped

    def StopRendering(self):
        self.stopped = True


class ResolveCancelTests(unittest.TestCase):
    def test_cancel_stops_active_render(self) -> None:
        project = RenderingProject()
        with self.assertRaises(RenderCancelled):
            _wait_for_render(
                project,
                "job",
                60,
                cancel_requested=lambda: True,
            )
        self.assertTrue(project.stopped)


if __name__ == "__main__":
    unittest.main()
