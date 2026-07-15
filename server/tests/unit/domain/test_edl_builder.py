from deadair.domain.edl_builder import BuildEdlConfig, build_edl, map_to_result_time, merge_overlapping
from deadair.domain.entities.edl import EdlSegment
from deadair.domain.value_objects.ids import VideoId
from deadair.domain.value_objects.time_range import TimeRange


def _kept(*ranges: TimeRange) -> tuple[EdlSegment, ...]:
    return tuple(EdlSegment(range=r) for r in ranges)


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
    assert edl.segments == _kept(TimeRange(0, 4.5), TimeRange(5.5, 10))


def test_overlapping_silence_and_filler_merge_into_one_cut():
    edl = build_edl(
        VideoId.new(),
        video_duration=10.0,
        silence_cut_ranges=[TimeRange(4, 6)],
        filler_cut_ranges=[TimeRange(5, 7)],
        config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.0),
    )
    assert edl.segments == _kept(TimeRange(0, 4), TimeRange(7, 10))


def test_tiny_keep_sliver_dropped_by_min_keep_duration():
    edl = build_edl(
        VideoId.new(),
        video_duration=10.0,
        silence_cut_ranges=[TimeRange(0, 4), TimeRange(4.2, 10)],
        filler_cut_ranges=[],
        config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.5),
    )
    # the sliver [4, 4.2) is shorter than min_keep_duration and gets dropped
    assert edl.segments == ()


def test_out_of_bounds_candidate_clamped():
    edl = build_edl(
        VideoId.new(),
        video_duration=5.0,
        silence_cut_ranges=[TimeRange(4, 20)],
        filler_cut_ranges=[],
        config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.0),
    )
    assert edl.segments == _kept(TimeRange(0, 4))
    assert edl.total_duration == 5.0


def test_no_candidates_keeps_whole_video():
    edl = build_edl(
        VideoId.new(),
        video_duration=8.0,
        silence_cut_ranges=[],
        filler_cut_ranges=[],
        config=BuildEdlConfig(),
    )
    assert edl.segments == _kept(TimeRange(0, 8.0))


def test_whole_video_cut_yields_no_keep_ranges():
    edl = build_edl(
        VideoId.new(),
        video_duration=5.0,
        silence_cut_ranges=[TimeRange(0, 5)],
        filler_cut_ranges=[],
        config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.0),
    )
    assert edl.segments == ()


def test_speed_multiplier_none_matches_plain_hard_cut_behavior():
    kwargs = dict(
        video_id=VideoId.new(),
        video_duration=10.0,
        silence_cut_ranges=[TimeRange(4, 6)],
        filler_cut_ranges=[],
    )
    plain = build_edl(config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.0), **kwargs)
    explicit_off = build_edl(
        config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.0, speed_multiplier=None), **kwargs
    )
    assert plain.segments == explicit_off.segments == _kept(TimeRange(0, 4), TimeRange(6, 10))


def test_speed_multiplier_retains_cut_as_sped_up_segment():
    edl = build_edl(
        VideoId.new(),
        video_duration=10.0,
        silence_cut_ranges=[TimeRange(4, 6)],
        filler_cut_ranges=[],
        config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.0, speed_multiplier=4.0),
    )
    assert edl.segments == (
        EdlSegment(range=TimeRange(0, 4), rate=1.0),
        EdlSegment(range=TimeRange(4, 6), rate=4.0),
        EdlSegment(range=TimeRange(6, 10), rate=1.0),
    )
    assert edl.cut_ranges() == ()


def test_speed_multiplier_whole_video_cut_becomes_one_sped_up_segment():
    edl = build_edl(
        VideoId.new(),
        video_duration=5.0,
        silence_cut_ranges=[TimeRange(0, 5)],
        filler_cut_ranges=[],
        config=BuildEdlConfig(padding_seconds=0.0, min_keep_duration=0.0, speed_multiplier=2.0),
    )
    assert edl.segments == (EdlSegment(range=TimeRange(0, 5), rate=2.0),)


def test_map_to_result_time_point_inside_a_keep_range():
    segments = _kept(TimeRange(0, 4), TimeRange(7, 10))
    # 2s into the first keep range -> 2s into the output
    assert map_to_result_time(2.0, segments) == 2.0
    # 8s is 1s into the second keep range, which starts at output position 4
    assert map_to_result_time(8.0, segments) == 5.0


def test_map_to_result_time_point_inside_a_cut_clamps_forward():
    segments = _kept(TimeRange(0, 4), TimeRange(7, 10))
    # 5s falls in the cut [4, 7) -- clamps to the elapsed kept duration so far (4)
    assert map_to_result_time(5.0, segments) == 4.0


def test_map_to_result_time_point_past_the_last_keep_range():
    segments = _kept(TimeRange(0, 4), TimeRange(7, 10))
    assert map_to_result_time(12.0, segments) == 7.0


def test_map_to_result_time_no_segments():
    assert map_to_result_time(3.0, []) == 0.0


def test_map_to_result_time_inside_a_sped_up_segment_scales_by_rate():
    segments = (
        EdlSegment(range=TimeRange(0, 4), rate=1.0),
        EdlSegment(range=TimeRange(4, 8), rate=4.0),  # 4s of source -> 1s of output
        EdlSegment(range=TimeRange(8, 10), rate=1.0),
    )
    # 2s into the sped-up segment -> 0.5s of output, landing at 4 + 0.5
    assert map_to_result_time(6.0, segments) == 4.5
    # past the sped-up segment: 4 (first segment) + 1 (sped-up segment, 4/4)
    assert map_to_result_time(9.0, segments) == 6.0
