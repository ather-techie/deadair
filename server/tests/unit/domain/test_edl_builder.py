from deadair.domain.edl_builder import BuildEdlConfig, build_edl, merge_overlapping
from deadair.domain.value_objects.ids import VideoId
from deadair.domain.value_objects.time_range import TimeRange


def test_merge_overlapping_merges_touching_and_overlapping_ranges():
    ranges = [TimeRange(0, 2), TimeRange(1, 3), TimeRange(5, 6)]
    assert merge_overlapping(ranges) == [TimeRange(0, 3), TimeRange(5, 6)]


def test_merge_overlapping_empty_input():
    assert merge_overlapping([]) == []


def test_single_silence_gap_with_padding_removed():
    edl = build_edl(
        VideoId.new(),
        video_duration=10.0,
        silence_cut_ranges=[TimeRange(4, 6)],
        filler_cut_ranges=[],
        config=BuildEdlConfig(padding_seconds=0.5, min_keep_duration=0.0),
    )
    assert edl.keep_ranges == (TimeRange(0, 4.5), TimeRange(5.5, 10))


def test_overlapping_silence_and_filler_merge_into_one_cut():
    edl = build_edl(
        VideoId.new(),
        video_duration=10.0,
        silence_cut_ranges=[TimeRange(4, 6)],
        filler_cut_ranges=[TimeRange(5, 7)],
        config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.0),
    )
    assert edl.keep_ranges == (TimeRange(0, 4), TimeRange(7, 10))


def test_tiny_keep_sliver_dropped_by_min_keep_duration():
    edl = build_edl(
        VideoId.new(),
        video_duration=10.0,
        silence_cut_ranges=[TimeRange(0, 4), TimeRange(4.2, 10)],
        filler_cut_ranges=[],
        config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.5),
    )
    # the sliver [4, 4.2) is shorter than min_keep_duration and gets dropped
    assert edl.keep_ranges == ()


def test_out_of_bounds_candidate_clamped():
    edl = build_edl(
        VideoId.new(),
        video_duration=5.0,
        silence_cut_ranges=[TimeRange(4, 20)],
        filler_cut_ranges=[],
        config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.0),
    )
    assert edl.keep_ranges == (TimeRange(0, 4),)
    assert edl.total_duration == 5.0


def test_no_candidates_keeps_whole_video():
    edl = build_edl(
        VideoId.new(),
        video_duration=8.0,
        silence_cut_ranges=[],
        filler_cut_ranges=[],
        config=BuildEdlConfig(),
    )
    assert edl.keep_ranges == (TimeRange(0, 8.0),)


def test_whole_video_cut_yields_no_keep_ranges():
    edl = build_edl(
        VideoId.new(),
        video_duration=5.0,
        silence_cut_ranges=[TimeRange(0, 5)],
        filler_cut_ranges=[],
        config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.0),
    )
    assert edl.keep_ranges == ()
