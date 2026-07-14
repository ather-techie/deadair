from collections.abc import Iterator
from dataclasses import dataclass

from deadair.domain.value_objects.ids import VideoId


@dataclass(frozen=True, slots=True)
class Word:
    text: str
    start: float
    end: float
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class Segment:
    words: tuple[Word, ...]
    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class Transcript:
    video_id: VideoId
    segments: tuple[Segment, ...]
    language: str

    def all_words(self) -> Iterator[Word]:
        for seg in self.segments:
            yield from seg.words
