from deadair.domain.policies.silence_policy import SilenceDetectionConfig, filter_cuttable_silences
from deadair.domain.value_objects.time_range import TimeRange


def test_filters_out_gaps_shorter_than_threshold():
    gaps = [TimeRange(0, 0.2), TimeRange(1, 2), TimeRange(3, 3.4)]
    config = SilenceDetectionConfig(min_silence_duration=0.5)
    result = filter_cuttable_silences(gaps, config)
    assert result == [TimeRange(1, 2)]


def test_gap_exactly_at_threshold_is_kept():
    gaps = [TimeRange(0, 0.5)]
    config = SilenceDetectionConfig(min_silence_duration=0.5)
    assert filter_cuttable_silences(gaps, config) == [TimeRange(0, 0.5)]


def test_empty_input_returns_empty():
    assert filter_cuttable_silences([], SilenceDetectionConfig()) == []
