from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlignmentUnit:
    text: str
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid alignment time: {self.start} -> {self.end}")


@dataclass(frozen=True)
class Cue:
    text: str
    start: float
    end: float

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Cue text cannot be empty")
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid cue time: {self.start} -> {self.end}")
