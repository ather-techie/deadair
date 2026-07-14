import pytest

from deadair.application.ports.video_repository import VideoRepository
from deadair.domain.entities.video import Video
from deadair.domain.value_objects.ids import VideoId


def _make_video(**overrides) -> Video:
    defaults = dict(
        id=VideoId.new(),
        source_path="/data/uploads/some-video.mp4",
        content_hash="deadbeef",
        duration_seconds=12.5,
        fps=30.0,
        width=1920,
        height=1080,
    )
    defaults.update(overrides)
    return Video(**defaults)


class VideoRepositoryContractTests:
    """Shared behavioral contract for any VideoRepository adapter. Subclass and
    provide a `repo` fixture returning a fresh adapter instance."""

    @pytest.fixture
    def repo(self) -> VideoRepository:
        raise NotImplementedError

    def test_add_then_get_returns_equal_video(self, repo):
        video = _make_video()
        repo.add(video)
        assert repo.get(video.id) == video

    def test_get_missing_returns_none(self, repo):
        assert repo.get(VideoId.new()) is None

    def test_list_all_returns_every_added_video(self, repo):
        video_a, video_b = _make_video(), _make_video()
        repo.add(video_a)
        repo.add(video_b)
        assert {v.id for v in repo.list_all()} == {video_a.id, video_b.id}

    def test_delete_removes_video(self, repo):
        video = _make_video()
        repo.add(video)
        repo.delete(video.id)
        assert repo.get(video.id) is None

    def test_delete_missing_is_a_noop(self, repo):
        repo.delete(VideoId.new())

    def test_add_video_with_optional_fields_unset(self, repo):
        video = _make_video(fps=None, width=None, height=None)
        repo.add(video)
        assert repo.get(video.id) == video
