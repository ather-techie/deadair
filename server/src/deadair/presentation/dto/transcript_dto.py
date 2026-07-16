from typing import Literal

from pydantic import BaseModel


class TranscriptSegmentDTO(BaseModel):
    start: float
    end: float
    text: str


class TranscriptDTO(BaseModel):
    language: str
    segments: list[TranscriptSegmentDTO]


class PartialTranscriptDTO(BaseModel):
    segments: list[TranscriptSegmentDTO]
    next_after: int
    finished: bool


class ResultTranscriptSegmentDTO(BaseModel):
    text: str
    original_start: float
    original_end: float
    result_start: float
    result_end: float


class ResultTranscriptDTO(BaseModel):
    language: str
    segments: list[ResultTranscriptSegmentDTO]


class HighlightedWordDTO(BaseModel):
    text: str
    start: float
    end: float
    status: Literal["kept", "sped_up", "removed"]


class HighlightedSegmentDTO(BaseModel):
    start: float
    end: float
    words: list[HighlightedWordDTO]


class HighlightedTranscriptDTO(BaseModel):
    language: str
    segments: list[HighlightedSegmentDTO]
