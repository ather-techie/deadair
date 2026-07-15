from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum

from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import JobId, VideoId


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED_CACHED = "skipped_cached"


class InvalidJobTransitionError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class StepState:
    step: PipelineStep
    status: StepStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    retryable: bool | None = None
    findings: dict[str, float] | None = None


_TERMINAL = (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED)


_STEP_TERMINAL = (StepStatus.DONE, StepStatus.SKIPPED_CACHED, StepStatus.FAILED)


def _derive_status(steps: tuple[StepState, ...]) -> JobStatus:
    statuses = {s.status for s in steps}
    if statuses <= set(_STEP_TERMINAL):
        # every step has settled -- the job itself can now become terminal
        return JobStatus.FAILED if StepStatus.FAILED in statuses else JobStatus.DONE
    if statuses & {StepStatus.RUNNING, StepStatus.DONE, StepStatus.SKIPPED_CACHED, StepStatus.FAILED}:
        return JobStatus.RUNNING
    return JobStatus.PENDING


@dataclass(frozen=True, slots=True)
class Job:
    id: JobId
    video_id: VideoId
    status: JobStatus
    steps: tuple[StepState, ...]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(video_id: VideoId, steps: Sequence[PipelineStep] = tuple(PipelineStep)) -> "Job":
        now = datetime.now(timezone.utc)
        return Job(
            id=JobId.new(),
            video_id=video_id,
            status=JobStatus.PENDING,
            steps=tuple(StepState(step=s, status=StepStatus.PENDING) for s in steps),
            created_at=now,
            updated_at=now,
        )

    def step_state(self, step: PipelineStep) -> StepState:
        return next(s for s in self.steps if s.step == step)

    def with_step_updated(
        self,
        step: PipelineStep,
        *,
        status: StepStatus,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error: str | None = None,
        retryable: bool | None = None,
        findings: dict[str, float] | None = None,
    ) -> "Job":
        if self.status in _TERMINAL:
            raise InvalidJobTransitionError(f"job {self.id} is terminal ({self.status})")
        new_steps = tuple(
            replace(
                s,
                status=status,
                started_at=started_at or s.started_at,
                finished_at=finished_at or s.finished_at,
                error=error,
                retryable=retryable,
                findings=findings,
            )
            if s.step == step
            else s
            for s in self.steps
        )
        return replace(
            self,
            steps=new_steps,
            status=_derive_status(new_steps),
            updated_at=datetime.now(timezone.utc),
        )

    def cancel(self) -> "Job":
        if self.status in _TERMINAL:
            raise InvalidJobTransitionError(f"job {self.id} is terminal ({self.status})")
        return replace(self, status=JobStatus.CANCELLED, updated_at=datetime.now(timezone.utc))
