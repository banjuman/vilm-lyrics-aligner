from __future__ import annotations

import sys
import threading
import time
import unittest

from lyrics_aligner.process_runner import JobCancelled, run_streaming_process


class ProcessRunnerTests(unittest.TestCase):
    def test_streams_utf8_output(self) -> None:
        lines = []
        result = run_streaming_process(
            [sys.executable, "-u", "-c", "print('첫 줄'); print('second')"],
            on_output=lines.append,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(lines, ["첫 줄", "second"])

    def test_cancel_does_not_wait_for_grandchild_stdout(self) -> None:
        cancel = threading.Event()

        def request_cancel() -> None:
            time.sleep(0.2)
            cancel.set()

        child_code = (
            "import subprocess,sys,time; "
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
            "time.sleep(30)"
        )
        threading.Thread(target=request_cancel, daemon=True).start()
        started = time.monotonic()
        with self.assertRaises(JobCancelled):
            run_streaming_process(
                [sys.executable, "-u", "-c", child_code],
                cancel_requested=cancel.is_set,
            )
        self.assertLess(time.monotonic() - started, 5)

    def test_cancels_a_running_process(self) -> None:
        cancel = threading.Event()

        def request_cancel() -> None:
            time.sleep(0.15)
            cancel.set()

        threading.Thread(target=request_cancel, daemon=True).start()
        started = time.monotonic()
        with self.assertRaises(JobCancelled):
            run_streaming_process(
                [sys.executable, "-u", "-c", "import time; time.sleep(30)"],
                cancel_requested=cancel.is_set,
            )
        self.assertLess(time.monotonic() - started, 5)


if __name__ == "__main__":
    unittest.main()
