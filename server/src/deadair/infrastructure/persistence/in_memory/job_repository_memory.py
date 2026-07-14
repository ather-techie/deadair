from deadair.application.ports.job_repository import (
    JobAlreadyExistsError,
    JobNotFoundError,
    JobRepository,
)
from deadair.domain.entities.job import Job, JobStatus
from deadair.domain.value_objects.ids import JobId, VideoId


class InMemoryJobRepository(JobRepository):
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def add(self, job: Job) -> None:
        if job.id.value in self._jobs:
            raise JobAlreadyExistsError(job.id)
        self._jobs[job.id.value] = job

    def get(self, job_id: JobId) -> Job | None:
        return self._jobs.get(job_id.value)

    def update(self, job: Job) -> None:
        if job.id.value not in self._jobs:
            raise JobNotFoundError(job.id)
        self._jobs[job.id.value] = job

    def list_for_video(self, video_id: VideoId) -> list[Job]:
        return sorted(
            (j for j in self._jobs.values() if j.video_id == video_id), key=lambda j: j.created_at
        )

    def list_active(self) -> list[Job]:
        return sorted(
            (j for j in self._jobs.values() if j.status in (JobStatus.PENDING, JobStatus.RUNNING)),
            key=lambda j: j.created_at,
        )
