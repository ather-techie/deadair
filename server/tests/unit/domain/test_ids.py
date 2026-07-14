import pytest

from deadair.domain.value_objects.ids import EdlId, JobId, TranscriptId, VideoId


@pytest.mark.parametrize("id_cls", [VideoId, JobId, TranscriptId, EdlId])
def test_new_generates_nonempty_unique_ids(id_cls):
    a, b = id_cls.new(), id_cls.new()
    assert a.value and b.value
    assert a != b


@pytest.mark.parametrize("id_cls", [VideoId, JobId, TranscriptId, EdlId])
def test_empty_value_raises(id_cls):
    with pytest.raises(ValueError):
        id_cls("")


def test_str_returns_value():
    vid = VideoId("abc-123")
    assert str(vid) == "abc-123"


def test_equal_values_are_equal():
    assert VideoId("x") == VideoId("x")
