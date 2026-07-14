from deadair.domain.entities.video import Video
from deadair.presentation.dto.video_dto import VideoDTO


def video_to_dto(video: Video) -> VideoDTO:
    return VideoDTO(
        id=video.id.value,
        source_path=video.source_path,
        content_hash=video.content_hash,
        duration_seconds=video.duration_seconds,
        fps=video.fps,
        width=video.width,
        height=video.height,
    )
