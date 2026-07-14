import pytest

from deadair.domain.value_objects.time_range import TimeRange


def test_duration():
    assert TimeRange(1.0, 3.5).duration == pytest.approx(2.5)


def test_negative_start_raises():
    with pytest.raises(ValueError):
        TimeRange(-1.0, 2.0)


def test_end_before_start_raises():
    with pytest.raises(ValueError):
        TimeRange(2.0, 1.0)


def test_zero_duration_is_allowed():
    assert TimeRange(2.0, 2.0).duration == 0.0


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (TimeRange(0, 5), TimeRange(3, 8), True),
        (TimeRange(0, 5), TimeRange(5, 8), False),
        (TimeRange(0, 5), TimeRange(6, 8), False),
        (TimeRange(0, 5), TimeRange(1, 2), True),
    ],
)
def test_overlaps(a, b, expected):
    assert a.overlaps(b) is expected
    assert b.overlaps(a) is expected


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (TimeRange(0, 5), TimeRange(5, 8), True),
        (TimeRange(0, 5), TimeRange(6, 8), False),
        (TimeRange(0, 5), TimeRange(3, 8), True),
    ],
)
def test_touches(a, b, expected):
    assert a.touches(b) is expected
    assert b.touches(a) is expected
