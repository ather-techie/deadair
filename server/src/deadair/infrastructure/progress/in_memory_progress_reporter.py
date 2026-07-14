from deadair.application.ports.progress_reporter import ProgressReporter
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import JobId


class InMemoryProgressReporter(ProgressReporter):
    def __init__(self) -> None:
        self._progress: dict[tuple[str, PipelineStep], tuple[float, str]] = {}

    def report(self, job_id: JobId, step: PipelineStep, fraction_complete: float, message: str = "") -> None:
        self._progress[(job_id.value, step)] = (fraction_complete, message)

    def get(self, job_id: JobId, step: PipelineStep) -> tuple[float, str] | None:
        return self._progress.get((job_id.value, step))
