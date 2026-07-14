from pydantic import BaseModel


class VideoDTO(BaseModel):
    id: str
    source_path: str
    content_hash: str
    duration_seconds: float
    fps: float | None = None
    width: int | None = None
    height: int | None = None


class UploadResponseDTO(BaseModel):
    video_id: str
    job_id: str
