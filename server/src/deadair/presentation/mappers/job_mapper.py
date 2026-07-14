from deadair.application.ports.progress_reporter import ProgressReporter
from deadair.domain.entities.job import Job, StepStatus
from deadair.presentation.dto.job_dto import JobDTO, StepStateDTO

_COMPLETE_STATUSES = (StepStatus.DONE, StepStatus.SKIPPED_CACHED)


def job_to_dto(job: Job, progress_reporter: ProgressReporter) -> JobDTO:
    steps = []
    for step_state in job.steps:
        if step_state.status in _COMPLETE_STATUSES:
            progress = 1.0
        elif step_state.status == StepStatus.RUNNING:
            reported = progress_reporter.get(job.id, step_state.step)
            progress = reported[0] if reported else 0.0
        else:
            progress = 0.0
        steps.append(
            StepStateDTO(
                step=step_state.step.value,
                status=step_state.status.value,
                progress=progress,
                error=step_state.error,
            )
        )
    return JobDTO(job_id=job.id.value, video_id=job.video_id.value, status=job.status.value, steps=steps)
