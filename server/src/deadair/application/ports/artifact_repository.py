from abc import ABC, abstractmethod

from deadair.domain.pipeline.artifact_key import ArtifactKey
from deadair.domain.value_objects.ids import VideoId


class ArtifactRepository(ABC):
    """Caches step outputs by (video_id, step, config_hash) — see
    domain/pipeline/config_hash.py for how the hash is computed. Milestone 1-2
    defines only this contract; no concrete adapter is built yet. Artifacts
    are opaque bytes: step-specific (de)serialization (e.g. Transcript<->JSON,
    or a manifest pointing at a large rendered file on disk) is an
    infrastructure decision made when each real adapter is built."""

    @abstractmethod
    def get(self, key: ArtifactKey) -> bytes | None: ...

    @abstractmethod
    def put(self, key: ArtifactKey, payload: bytes) -> None: ...

    @abstractmethod
    def exists(self, key: ArtifactKey) -> bool: ...

    @abstractmethod
    def invalidate_video(self, video_id: VideoId) -> None:
        """Delete all cached artifacts for a video (re-upload/delete)."""
