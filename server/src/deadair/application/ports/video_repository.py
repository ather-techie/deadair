from abc import ABC, abstractmethod

from deadair.domain.entities.video import Video
from deadair.domain.value_objects.ids import VideoId


class VideoRepository(ABC):
    """Persists uploaded Video metadata (not the file bytes themselves)."""

    @abstractmethod
    def add(self, video: Video) -> None: ...

    @abstractmethod
    def get(self, video_id: VideoId) -> Video | None: ...

    @abstractmethod
    def list_all(self) -> list[Video]: ...

    @abstractmethod
    def delete(self, video_id: VideoId) -> None: ...
