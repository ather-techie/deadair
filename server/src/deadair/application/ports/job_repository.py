from abc import ABC, abstractmethod

from deadair.domain.entities.job import Job
from deadair.domain.value_objects.ids import JobId, VideoId


class JobRepositoryError(Exception):
    pass


class JobNotFoundError(JobRepositoryError):
    def __init__(self, job_id: JobId):
        super().__init__(f"job not found: {job_id}")
        self.job_id = job_id


class JobAlreadyExistsError(JobRepositoryError):
    def __init__(self, job_id: JobId):
        super().__init__(f"job already exists: {job_id}")
        self.job_id = job_id


class JobRepository(ABC):
    """Persists Job aggregates. A Job (including its full StepState tuple) is
    the unit of consistency — callers never read/write individual steps."""

    @abstractmethod
    def add(self, job: Job) -> None:
        """Raises JobAlreadyExistsError if job.id already exists."""

    @abstractmethod
    def get(self, job_id: JobId) -> Job | None: ...

    @abstractmethod
    def update(self, job: Job) -> None:
        """Raises JobNotFoundError if job.id doesn't exist yet."""

    @abstractmethod
    def list_for_video(self, video_id: VideoId) -> list[Job]:
        """Ordered by created_at ascending."""

    @abstractmethod
    def list_active(self) -> list[Job]:
        """Jobs with status PENDING or RUNNING, ordered by created_at ascending."""
