from deadair.domain.entities.edl import EDL, EdlSegment
from deadair.domain.entities.transcript import Segment, Transcript, Word
from deadair.domain.value_objects.ids import VideoId
from deadair.domain.value_objects.time_range import TimeRange
from deadair.presentation.mappers.transcript_mapper import build_result_transcript


def _transcript(video_id: VideoId) -> Transcript:
    words = (
        Word(text="um", start=0.0, end=0.4, confidence=0.9),
        Word(text="hello", start=0.4, end=0.9, confidence=0.98),
        Word(text="world", start=0.9, end=1.3, confidence=0.97),
    )
    segment = Segment(words=words, start=0.0, end=1.3, text="um hello world")
    return Transcript(video_id=video_id, segments=(segment,), language="en")


def test_words_outside_keep_ranges_are_dropped_and_remaining_text_rejoined():
    video_id = VideoId.new()
    transcript = _transcript(video_id)
    # "um" (0.0-0.4) is cut; "hello world" (0.4-1.3) survives, shifted to start at 0 in the output
    edl = EDL(video_id=video_id, segments=(EdlSegment(range=TimeRange(0.4, 1.3)),), total_duration=1.3)

    result = build_result_transcript(transcript, edl)

    assert len(result.segments) == 1
    seg = result.segments[0]
    assert seg.text == "hello world"
    assert seg.original_start == 0.4
    assert seg.original_end == 1.3
    assert seg.result_start == 0.0
    assert seg.result_end == 0.9


def test_segment_fully_cut_is_dropped_entirely():
    video_id = VideoId.new()
    transcript = _transcript(video_id)
    edl = EDL(video_id=video_id, segments=(), total_duration=1.3)

    result = build_result_transcript(transcript, edl)

    assert result.segments == []


def test_no_cuts_keeps_all_words_and_original_timestamps():
    video_id = VideoId.new()
    transcript = _transcript(video_id)
    edl = EDL(video_id=video_id, segments=(EdlSegment(range=TimeRange(0.0, 1.3)),), total_duration=1.3)

    result = build_result_transcript(transcript, edl)

    assert len(result.segments) == 1
    seg = result.segments[0]
    assert seg.text == "um hello world"
    assert seg.original_start == seg.result_start == 0.0
    assert seg.original_end == seg.result_end == 1.3


def test_words_in_a_sped_up_segment_survive_and_are_remapped():
    video_id = VideoId.new()
    transcript = _transcript(video_id)
    # "um" (0.0-0.4) is sped up 4x instead of cut; "hello world" (0.4-1.3) is normal speed
    edl = EDL(
        video_id=video_id,
        segments=(
            EdlSegment(range=TimeRange(0.0, 0.4), rate=4.0),
            EdlSegment(range=TimeRange(0.4, 1.3), rate=1.0),
        ),
        total_duration=1.3,
    )

    result = build_result_transcript(transcript, edl)

    assert len(result.segments) == 1
    seg = result.segments[0]
    assert seg.text == "um hello world"
    assert seg.original_start == 0.0
    assert seg.original_end == 1.3
    assert seg.result_start == 0.0
    assert seg.result_end == 0.1 + 0.9  # 0.4s of "um" at 4x (0.1s) + 0.9s of normal-speed remainder
