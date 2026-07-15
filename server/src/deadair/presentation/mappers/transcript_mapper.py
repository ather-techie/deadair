from deadair.domain.entities.transcript import Segment, Transcript
from deadair.presentation.dto.transcript_dto import (
    PartialTranscriptDTO,
    TranscriptDTO,
    TranscriptSegmentDTO,
)


def _segment_to_dto(segment: Segment) -> TranscriptSegmentDTO:
    return TranscriptSegmentDTO(start=segment.start, end=segment.end, text=segment.text)


def transcript_to_dto(transcript: Transcript) -> TranscriptDTO:
    return TranscriptDTO(
        language=transcript.language,
        segments=[_segment_to_dto(seg) for seg in transcript.segments],
    )


def partial_transcript_to_dto(
    indexed_segments: list[tuple[int, Segment]], after_index: int, finished: bool
) -> PartialTranscriptDTO:
    next_after = indexed_segments[-1][0] if indexed_segments else after_index
    return PartialTranscriptDTO(
        segments=[_segment_to_dto(seg) for _, seg in indexed_segments],
        next_after=next_after,
        finished=finished,
    )
