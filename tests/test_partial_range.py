from __future__ import annotations

import unittest

from lyrics_aligner.matching import CueTranscriptMatch
from lyrics_aligner.pipeline import _partial_lyric_span


def match(index: int, *, usable: bool) -> CueTranscriptMatch:
    return CueTranscriptMatch(
        cue_index=index,
        source_text=f"line {index}",
        transcript_text=f"line {index}" if usable else "",
        start=float(index) if usable else None,
        end=float(index + 1) if usable else None,
        similarity=0.9 if usable else 0.1,
        coverage=0.9 if usable else 0.1,
        exact_characters=4 if usable else 0,
        status="match" if usable else "weak",
    )


class PartialRangeTests(unittest.TestCase):
    def test_selects_only_continuous_anchored_source_span(self) -> None:
        matches = [match(i, usable=i in {4, 5, 6}) for i in range(12)]
        self.assertEqual(_partial_lyric_span(matches), (4, 6))

    def test_refuses_to_force_align_full_lyrics_without_anchor(self) -> None:
        self.assertIsNone(_partial_lyric_span([match(i, usable=False) for i in range(8)]))


if __name__ == "__main__":
    unittest.main()
