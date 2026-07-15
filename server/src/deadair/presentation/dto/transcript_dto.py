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
