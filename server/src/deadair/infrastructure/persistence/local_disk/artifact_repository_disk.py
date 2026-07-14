import os
import shutil
from pathlib import Path

from deadair.application.ports.artifact_repository import ArtifactRepository
from deadair.domain.pipeline.artifact_key import ArtifactKey
from deadair.domain.value_objects.ids import VideoId


class DiskArtifactRepository(ArtifactRepository):
    """Stores opaque artifact bytes under
    {artifacts_dir}/{video_id}/{step}/{config_hash}.bin."""

    def __init__(self, artifacts_dir: Path):
        self._artifacts_dir = Path(artifacts_dir)

    def _path_for(self, key: ArtifactKey) -> Path:
        return self._artifacts_dir / key.video_id.value / key.step.value / f"{key.config_hash}.bin"

    def get(self, key: ArtifactKey) -> bytes | None:
        path = self._path_for(key)
        return path.read_bytes() if path.exists() else None

    def put(self, key: ArtifactKey, payload: bytes) -> None:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_bytes(payload)
        os.replace(tmp_path, path)

    def exists(self, key: ArtifactKey) -> bool:
        return self._path_for(key).exists()

    def invalidate_video(self, video_id: VideoId) -> None:
        shutil.rmtree(self._artifacts_dir / video_id.value, ignore_errors=True)
