from pydantic import BaseModel


class StepStateDTO(BaseModel):
    step: str
    status: str
    progress: float
    error: str | None = None
    findings: dict[str, float] | None = None


class JobDTO(BaseModel):
    job_id: str
    video_id: str
    status: str
    steps: list[StepStateDTO]
