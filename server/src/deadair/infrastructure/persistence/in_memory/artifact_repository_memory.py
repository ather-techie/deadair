from deadair.application.ports.artifact_repository import ArtifactRepository
from deadair.domain.pipeline.artifact_key import ArtifactKey
from deadair.domain.value_objects.ids import VideoId


class InMemoryArtifactRepository(ArtifactRepository):
    def __init__(self) -> None:
        self._artifacts: dict[ArtifactKey, bytes] = {}

    def get(self, key: ArtifactKey) -> bytes | None:
        return self._artifacts.get(key)

    def put(self, key: ArtifactKey, payload: bytes) -> None:
        self._artifacts[key] = payload

    def exists(self, key: ArtifactKey) -> bool:
        return key in self._artifacts

    def invalidate_video(self, video_id: VideoId) -> None:
        for key in [k for k in self._artifacts if k.video_id == video_id]:
            del self._artifacts[key]
