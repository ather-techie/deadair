from deadair.domain.entities.video import Video
from deadair.domain.value_objects.ids import VideoId


def test_video_construction_and_equality():
    vid = VideoId.new()
    v1 = Video(id=vid, source_path="/tmp/a.mp4", content_hash="abc", duration_seconds=10.0)
    v2 = Video(id=vid, source_path="/tmp/a.mp4", content_hash="abc", duration_seconds=10.0)
    assert v1 == v2


def test_video_optional_fields_default_to_none():
    v = Video(id=VideoId.new(), source_path="/tmp/a.mp4", content_hash="abc", duration_seconds=10.0)
    assert v.fps is None
    assert v.width is None
    assert v.height is None
