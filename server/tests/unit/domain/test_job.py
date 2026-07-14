import pytest

from deadair.domain.entities.job import (
    InvalidJobTransitionError,
    Job,
    JobStatus,
    StepStatus,
)
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import VideoId


def _all_pending_job():
    return Job.create(VideoId.new())


def test_create_job_is_pending_with_all_steps_pending():
    job = Job.create(VideoId.new())
    assert job.status == JobStatus.PENDING
    assert len(job.steps) == len(list(PipelineStep))
    assert all(s.status == StepStatus.PENDING for s in job.steps)


def test_marking_one_step_running_makes_job_running():
    job = _all_pending_job()
    job = job.with_step_updated(PipelineStep.EXTRACT_AUDIO, status=StepStatus.RUNNING)
    assert job.status == JobStatus.RUNNING


def test_marking_all_steps_done_makes_job_done():
    job = _all_pending_job()
    for step in PipelineStep:
        job = job.with_step_updated(step, status=StepStatus.DONE)
    assert job.status == JobStatus.DONE


def test_skipped_cached_counts_as_done():
    job = _all_pending_job()
    for step in PipelineStep:
        job = job.with_step_updated(step, status=StepStatus.SKIPPED_CACHED)
    assert job.status == JobStatus.DONE


def test_any_failed_step_makes_job_failed():
    job = _all_pending_job()
    job = job.with_step_updated(PipelineStep.EXTRACT_AUDIO, status=StepStatus.DONE)
    job = job.with_step_updated(PipelineStep.TRANSCRIBE, status=StepStatus.FAILED, error="boom", retryable=True)
    assert job.status == JobStatus.FAILED
    assert job.step_state(PipelineStep.TRANSCRIBE).error == "boom"
    assert job.step_state(PipelineStep.TRANSCRIBE).retryable is True


@pytest.mark.parametrize("terminal_status", [JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED])
def test_updating_a_step_on_terminal_job_raises(terminal_status):
    job = _all_pending_job()
    for step in PipelineStep:
        job = job.with_step_updated(step, status=StepStatus.DONE)
    from dataclasses import replace

    job = replace(job, status=terminal_status)
    with pytest.raises(InvalidJobTransitionError):
        job.with_step_updated(PipelineStep.EXTRACT_AUDIO, status=StepStatus.RUNNING)


def test_cancel_sets_cancelled_status():
    job = _all_pending_job()
    cancelled = job.cancel()
    assert cancelled.status == JobStatus.CANCELLED


def test_cancel_terminal_job_raises():
    job = _all_pending_job().cancel()
    with pytest.raises(InvalidJobTransitionError):
        job.cancel()


def test_step_state_returns_correct_step():
    job = _all_pending_job()
    state = job.step_state(PipelineStep.RENDER)
    assert state.step == PipelineStep.RENDER
