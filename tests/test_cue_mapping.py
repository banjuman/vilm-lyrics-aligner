import unittest

from lyrics_aligner.cue_mapping import map_units_to_optional_cues
from lyrics_aligner.models import AlignmentUnit


class OptionalCueMappingTests(unittest.TestCase):
    def test_keeps_missing_tail_cue_as_none(self):
        result = map_units_to_optional_cues(
            ["first line", "missing tail"],
            [AlignmentUnit("first line", 1.0, 2.0)],
        )
        self.assertIsNotNone(result[0])
        self.assertIsNone(result[1])


if __name__ == "__main__":
    unittest.main()
