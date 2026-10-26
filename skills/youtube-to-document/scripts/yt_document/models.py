from dataclasses import dataclass
from itertools import pairwise
from math import isfinite


@dataclass(frozen=True)
class Segment:

    start: float
    end: float
    text: str

    def __post_init__(self) -> None:
        if not isfinite(self.start) or not isfinite(self.end):
            raise ValueError("Segment timestamps must be finite.")

        if self.start < 0:
            raise ValueError("Segment start must be nonnegative.")

        if self.end <= self.start:
            raise ValueError("Segment end must be after its start.")

        if not self.text.strip():
            raise ValueError("Segment text must not be blank.")


@dataclass(frozen=True)
class Transcript:

    title: str
    source_url: str
    language: str
    segments: tuple[Segment, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("Transcript must contain at least one segment.")

        for previous, current in pairwise(self.segments):
            if current.start < previous.start:
                raise ValueError(
                    "Transcript segments must be ordered by start time."
                )