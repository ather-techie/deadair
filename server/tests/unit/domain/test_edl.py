import pytest

from deadair.domain.entities.edl import EDL, EdlSegment
from deadair.domain.value_objects.ids import VideoId
from deadair.domain.value_objects.time_range import TimeRange


def _kept(*ranges: TimeRange) -> tuple[EdlSegment, ...]:
    return tuple(EdlSegment(range=r) for r in ranges)


def test_valid_edl_construction():
    edl = EDL(
        video_id=VideoId.new(),
        segments=_kept(TimeRange(0, 2), TimeRange(3, 5)),
        total_duration=5.0,
    )
    assert edl.segments[0].range.start == 0


def test_unsorted_segments_raise():
    with pytest.raises(ValueError):
        EDL(
            video_id=VideoId.new(),
            segments=_kept(TimeRange(3, 5), TimeRange(0, 2)),
            total_duration=5.0,
        )


def test_overlapping_segments_raise():
    with pytest.raises(ValueError):
        EDL(
            video_id=VideoId.new(),
            segments=_kept(TimeRange(0, 3), TimeRange(2, 5)),
            total_duration=5.0,
        )


def test_out_of_bounds_segment_raises():
    with pytest.raises(ValueError):
        EDL(
            video_id=VideoId.new(),
            segments=_kept(TimeRange(0, 6)),
            total_duration=5.0,
        )


def test_negative_total_duration_raises():
    with pytest.raises(ValueError):
        EDL(video_id=VideoId.new(), segments=(), total_duration=-1.0)


def test_zero_or_negative_rate_raises():
    with pytest.raises(ValueError):
        EdlSegment(range=TimeRange(0, 1), rate=0)
    with pytest.raises(ValueError):
        EdlSegment(range=TimeRange(0, 1), rate=-2.0)


def test_cut_ranges_is_complement_with_gaps():
    edl = EDL(
        video_id=VideoId.new(),
        segments=_kept(TimeRange(1, 2), TimeRange(4, 5)),
        total_duration=6.0,
    )
    assert edl.cut_ranges() == (TimeRange(0, 1), TimeRange(2, 4), TimeRange(5, 6))


def test_cut_ranges_empty_when_fully_kept():
    edl = EDL(video_id=VideoId.new(), segments=_kept(TimeRange(0, 5)), total_duration=5.0)
    assert edl.cut_ranges() == ()


def test_cut_ranges_full_video_when_nothing_kept():
    edl = EDL(video_id=VideoId.new(), segments=(), total_duration=5.0)
    assert edl.cut_ranges() == (TimeRange(0, 5),)


def test_cut_ranges_excludes_sped_up_segments():
    # a sped-up segment is present in the output, so it's not a "cut" -- only
    # the true gap between the two segments is.
    edl = EDL(
        video_id=VideoId.new(),
        segments=(
            EdlSegment(range=TimeRange(0, 2), rate=1.0),
            EdlSegment(range=TimeRange(2, 3), rate=4.0),
            EdlSegment(range=TimeRange(4, 6), rate=1.0),
        ),
        total_duration=6.0,
    )
    assert edl.cut_ranges() == (TimeRange(3, 4),)
