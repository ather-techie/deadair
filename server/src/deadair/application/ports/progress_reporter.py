from abc import ABC, abstractmethod

from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import JobId


class ProgressReporter(ABC):
    """Sink for fine-grained in-step progress (e.g. Whisper % complete),
    distinct from JobRepository which persists coarse step/status
    transitions. A later adapter might push to Redis pub/sub for polling."""

    @abstractmethod
    def report(self, job_id: JobId, step: PipelineStep, fraction_complete: float, message: str = "") -> None: ...

    @abstractmethod
    def get(self, job_id: JobId, step: PipelineStep) -> tuple[float, str] | None:
        """Returns the last-reported (fraction_complete, message) for this
        job/step, or None if nothing has been reported yet. Used by the API
        layer to render polling progress."""
