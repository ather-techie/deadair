import pytest
from hypothesis import given
from hypothesis import strategies as st

from deadair.domain.edl_builder import BuildEdlConfig, build_edl
from deadair.domain.value_objects.ids import VideoId
from deadair.domain.value_objects.time_range import TimeRange

durations = st.floats(min_value=1.0, max_value=600.0, allow_nan=False, allow_infinity=False)


def _range_strategy(duration):
    # Draw two floats and sort them into (start, end) rather than
    # constructing TimeRange eagerly and filtering — TimeRange.__post_init__
    # raises on end < start, which happens *before* a .filter() ever runs.
    return st.tuples(
        st.floats(min_value=0, max_value=duration, allow_nan=False),
        st.floats(min_value=0, max_value=duration, allow_nan=False),
    ).map(lambda pair: TimeRange(min(pair), max(pair)))


@given(duration=durations, data=st.data())
def test_keep_and_cut_ranges_partition_timeline_with_no_gaps_or_overlaps(duration, data):
    range_strategy = _range_strategy(duration)
    silences = data.draw(st.lists(range_strategy, max_size=15))
    fillers = data.draw(st.lists(range_strategy, max_size=15))
    padding = data.draw(st.floats(min_value=0.0, max_value=2.0, allow_nan=False))
    min_keep = data.draw(st.floats(min_value=0.0, max_value=2.0, allow_nan=False))

    edl = build_edl(
        VideoId.new(),
        duration,
        silences,
        fillers,
        BuildEdlConfig(padding_seconds=padding, min_keep_duration=min_keep),
    )

    all_ranges = sorted(
        [s.range for s in edl.segments] + list(edl.cut_ranges()), key=lambda r: r.start
    )
    cursor = 0.0
    for r in all_ranges:
        assert r.start == pytest.approx(cursor, abs=1e-6)
        cursor = r.end
    assert cursor == pytest.approx(duration, abs=1e-6)


@given(duration=durations, data=st.data())
def test_build_edl_never_raises_and_produces_a_valid_edl(duration, data):
    range_strategy = _range_strategy(duration)
    silences = data.draw(st.lists(range_strategy, max_size=15))
    fillers = data.draw(st.lists(range_strategy, max_size=15))
    padding = data.draw(st.floats(min_value=0.0, max_value=2.0, allow_nan=False))
    min_keep = data.draw(st.floats(min_value=0.0, max_value=2.0, allow_nan=False))

    edl = build_edl(
        VideoId.new(),
        duration,
        silences,
        fillers,
        BuildEdlConfig(padding_seconds=padding, min_keep_duration=min_keep),
    )
    assert edl.total_duration == duration
    for s in edl.segments:
        assert 0.0 <= s.range.start <= s.range.end <= duration


@given(duration=durations, data=st.data())
def test_kept_ranges_meet_min_keep_duration_or_are_absent(duration, data):
    range_strategy = _range_strategy(duration)
    silences = data.draw(st.lists(range_strategy, max_size=15))
    fillers = data.draw(st.lists(range_strategy, max_size=15))
    padding = data.draw(st.floats(min_value=0.0, max_value=2.0, allow_nan=False))
    min_keep = data.draw(st.floats(min_value=0.0, max_value=2.0, allow_nan=False))

    edl = build_edl(
        VideoId.new(),
        duration,
        silences,
        fillers,
        BuildEdlConfig(padding_seconds=padding, min_keep_duration=min_keep),
    )
    for s in edl.segments:
        assert s.range.duration >= min_keep - 1e-9
