import pytest

from deadair.domain.entities.edl import EDL
from deadair.domain.value_objects.ids import VideoId
from deadair.domain.value_objects.time_range import TimeRange


def test_valid_edl_construction():
    edl = EDL(
        video_id=VideoId.new(),
        keep_ranges=(TimeRange(0, 2), TimeRange(3, 5)),
        total_duration=5.0,
    )
    assert edl.keep_ranges[0].start == 0


def test_unsorted_keep_ranges_raise():
    with pytest.raises(ValueError):
        EDL(
            video_id=VideoId.new(),
            keep_ranges=(TimeRange(3, 5), TimeRange(0, 2)),
            total_duration=5.0,
        )


def test_overlapping_keep_ranges_raise():
    with pytest.raises(ValueError):
        EDL(
            video_id=VideoId.new(),
            keep_ranges=(TimeRange(0, 3), TimeRange(2, 5)),
            total_duration=5.0,
        )


def test_out_of_bounds_keep_range_raises():
    with pytest.raises(ValueError):
        EDL(
            video_id=VideoId.new(),
            keep_ranges=(TimeRange(0, 6),),
            total_duration=5.0,
        )


def test_negative_total_duration_raises():
    with pytest.raises(ValueError):
        EDL(video_id=VideoId.new(), keep_ranges=(), total_duration=-1.0)


def test_cut_ranges_is_complement_with_gaps():
    edl = EDL(
        video_id=VideoId.new(),
        keep_ranges=(TimeRange(1, 2), TimeRange(4, 5)),
        total_duration=6.0,
    )
    assert edl.cut_ranges() == (TimeRange(0, 1), TimeRange(2, 4), TimeRange(5, 6))


def test_cut_ranges_empty_when_fully_kept():
    edl = EDL(video_id=VideoId.new(), keep_ranges=(TimeRange(0, 5),), total_duration=5.0)
    assert edl.cut_ranges() == ()


def test_cut_ranges_full_video_when_nothing_kept():
    edl = EDL(video_id=VideoId.new(), keep_ranges=(), total_duration=5.0)
    assert edl.cut_ranges() == (TimeRange(0, 5),)
