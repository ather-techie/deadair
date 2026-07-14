import pytest

from deadair.application.ports.artifact_repository import ArtifactRepository
from deadair.domain.pipeline.artifact_key import ArtifactKey
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import VideoId


class ArtifactRepositoryContractTests:
    """Shared behavioral contract for any ArtifactRepository adapter. Subclass
    and provide a `repo` fixture returning a fresh adapter instance."""

    @pytest.fixture
    def repo(self) -> ArtifactRepository:
        raise NotImplementedError

    def test_put_then_get_returns_same_bytes(self, repo):
        key = ArtifactKey(VideoId.new(), PipelineStep.EXTRACT_AUDIO, "hash-1")
        repo.put(key, b"payload-bytes")
        assert repo.get(key) == b"payload-bytes"

    def test_get_missing_returns_none(self, repo):
        key = ArtifactKey(VideoId.new(), PipelineStep.EXTRACT_AUDIO, "hash-1")
        assert repo.get(key) is None

    def test_exists_reflects_put(self, repo):
        key = ArtifactKey(VideoId.new(), PipelineStep.TRANSCRIBE, "hash-2")
        assert repo.exists(key) is False
        repo.put(key, b"data")
        assert repo.exists(key) is True

    def test_put_overwrites_existing_payload(self, repo):
        key = ArtifactKey(VideoId.new(), PipelineStep.BUILD_EDL, "hash-3")
        repo.put(key, b"first")
        repo.put(key, b"second")
        assert repo.get(key) == b"second"

    def test_invalidate_video_removes_only_that_videos_artifacts(self, repo):
        video_a, video_b = VideoId.new(), VideoId.new()
        key_a = ArtifactKey(video_a, PipelineStep.EXTRACT_AUDIO, "hash-a")
        key_a2 = ArtifactKey(video_a, PipelineStep.TRANSCRIBE, "hash-a2")
        key_b = ArtifactKey(video_b, PipelineStep.EXTRACT_AUDIO, "hash-b")
        repo.put(key_a, b"a")
        repo.put(key_a2, b"a2")
        repo.put(key_b, b"b")

        repo.invalidate_video(video_a)

        assert repo.get(key_a) is None
        assert repo.get(key_a2) is None
        assert repo.get(key_b) == b"b"

    def test_invalidate_missing_video_is_a_noop(self, repo):
        repo.invalidate_video(VideoId.new())
