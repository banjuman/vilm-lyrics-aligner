
import unittest

from lyrics_aligner.models import AlignmentUnit, Cue
from lyrics_aligner.segmentation import auto_segment_source_cues


class AutomaticSegmentationTests(unittest.TestCase):
    def segment(self, text, cue, units):
        return auto_segment_source_cues(
            [text], {0: cue}, units, local_units_by_index={0: units}
        )[0]

    def test_keeps_dense_rap_line_above_preferred_character_count(self):
        words = "special vibe song han river han gang in the moon".split()
        units = [
            AlignmentUnit(word, index * 0.45, index * 0.45 + 0.4)
            for index, word in enumerate(words)
        ]
        cue = Cue(" ".join(words), 0.0, 4.45)
        self.assertEqual(self.segment(cue.text, cue, units), [cue])

    def test_splits_short_line_at_clear_internal_sung_pause(self):
        text = "의리라도 괜찮은데"
        cue = Cue(text, 1.0, 7.0)
        units = [
            AlignmentUnit("의리라도", 1.0, 2.4),
            AlignmentUnit("괜찮은데", 5.4, 7.0),
        ]
        result = self.segment(text, cue, units)
        self.assertEqual([item.text for item in result], ["의리라도", "괜찮은데"])
        self.assertEqual((result[0].start, result[0].end), (1.0, 2.4))
        self.assertEqual((result[1].start, result[1].end), (5.4, 7.0))

    def test_splits_short_punctuated_phrases_consistently(self):
        text = "안되나요. 어렵나요."
        for second_start in (2.3, 3.0):
            with self.subTest(second_start=second_start):
                cue = Cue(text, 0.0, second_start + 1.0)
                units = [
                    AlignmentUnit("안되나요.", 0.0, 1.0),
                    AlignmentUnit("어렵나요.", second_start, second_start + 1.0),
                ]
                result = self.segment(text, cue, units)
                self.assertEqual(
                    [item.text for item in result], ["안되나요.", "어렵나요."]
                )

    def test_does_not_split_short_unpunctuated_phrase_at_moderate_gap(self):
        text = "우리 함께"
        cue = Cue(text, 0.0, 3.3)
        units = [
            AlignmentUnit("우리", 0.0, 1.0),
            AlignmentUnit("함께", 2.3, 3.3),
        ]
        self.assertEqual(self.segment(text, cue, units), [cue])

    def test_splits_slower_long_duration_line_even_below_hard_limit(self):
        words = "한강 공원에 짙게 배인 검은 정글 사이에 불어대는 초록의 향연".split()
        units = [
            AlignmentUnit(word, index * 0.8, index * 0.8 + 0.65)
            for index, word in enumerate(words)
        ]
        cue = Cue(" ".join(words), 0.0, 7.05)
        result = self.segment(cue.text, cue, units)
        self.assertGreater(len(result), 1)
        self.assertEqual(" ".join(item.text for item in result), cue.text)

    def test_preserves_source_line_without_timing_evidence(self):
        cue = Cue("짧은 한 소절", 1.0, 3.0)
        self.assertEqual(self.segment(cue.text, cue, []), [cue])


if __name__ == "__main__":
    unittest.main()
