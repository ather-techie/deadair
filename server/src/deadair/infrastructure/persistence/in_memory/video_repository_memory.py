from deadair.application.ports.video_repository import VideoRepository
from deadair.domain.entities.video import Video
from deadair.domain.value_objects.ids import VideoId


class InMemoryVideoRepository(VideoRepository):
    def __init__(self) -> None:
        self._videos: dict[str, Video] = {}

    def add(self, video: Video) -> None:
        self._videos[video.id.value] = video

    def get(self, video_id: VideoId) -> Video | None:
        return self._videos.get(video_id.value)

    def list_all(self) -> list[Video]:
        return list(self._videos.values())

    def delete(self, video_id: VideoId) -> None:
        self._videos.pop(video_id.value, None)
