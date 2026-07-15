from datetime import datetime

from pydantic import BaseModel


class StepStateDTO(BaseModel):
    step: str
    status: str
    progress: float
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    findings: dict[str, float] | None = None


class JobDTO(BaseModel):
    job_id: str
    video_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    steps: list[StepStateDTO]
