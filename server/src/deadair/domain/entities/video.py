from dataclasses import dataclass

from deadair.domain.value_objects.ids import VideoId


@dataclass(frozen=True, slots=True)
class Video:
    id: VideoId
    source_path: str
    content_hash: str
    duration_seconds: float
    fps: float | None = None
    width: int | None = None
    height: int | None = None
