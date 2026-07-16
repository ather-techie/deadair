from deadair.domain.edl_builder import map_to_result_time
from deadair.domain.entities.edl import EDL, EdlSegment
from deadair.domain.entities.transcript import Segment, Transcript, Word
from deadair.domain.value_objects.time_range import TimeRange
from deadair.presentation.dto.transcript_dto import (
    HighlightedSegmentDTO,
    HighlightedTranscriptDTO,
    HighlightedWordDTO,
    PartialTranscriptDTO,
    ResultTranscriptDTO,
    ResultTranscriptSegmentDTO,
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


def build_result_transcript(transcript: Transcript, edl: EDL) -> ResultTranscriptDTO:
    """Filters each segment down to only the words that survive the EDL's
    cuts (present in some segment, whether at normal speed or sped up),
    dropping segments left with no words, and remaps the surviving words'
    start/end onto the trimmed-output timeline."""
    segments: list[ResultTranscriptSegmentDTO] = []
    for seg in transcript.segments:
        kept = [
            w for w in seg.words if any(TimeRange(w.start, w.end).overlaps(s.range) for s in edl.segments)
        ]
        if not kept:
            continue
        segments.append(
            ResultTranscriptSegmentDTO(
                text=" ".join(w.text for w in kept),
                original_start=kept[0].start,
                original_end=kept[-1].end,
                result_start=map_to_result_time(kept[0].start, edl.segments),
                result_end=map_to_result_time(kept[-1].end, edl.segments),
            )
        )
    return ResultTranscriptDTO(language=transcript.language, segments=segments)


def _word_status(word: Word, edl_segments: list[EdlSegment]) -> str:
    overlapping = [s for s in edl_segments if TimeRange(word.start, word.end).overlaps(s.range)]
    if not overlapping:
        return "removed"
    if any(s.rate == 1.0 for s in overlapping):
        return "kept"
    return "sped_up"


def build_highlighted_transcript(transcript: Transcript, edl: EDL) -> HighlightedTranscriptDTO:
    """Tags every original word as kept/sped_up/removed by overlapping its timestamp
    against the EDL's segments, without dropping or remapping anything -- this stays
    on the original timeline for inline highlighting of the original transcript."""
    segments = [
        HighlightedSegmentDTO(
            start=seg.start,
            end=seg.end,
            words=[
                HighlightedWordDTO(
                    text=w.text, start=w.start, end=w.end, status=_word_status(w, list(edl.segments))
                )
                for w in seg.words
            ],
        )
        for seg in transcript.segments
    ]
    return HighlightedTranscriptDTO(language=transcript.language, segments=segments)
