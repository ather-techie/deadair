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
