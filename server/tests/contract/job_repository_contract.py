import pytest

from deadair.application.ports.job_repository import (
    JobAlreadyExistsError,
    JobNotFoundError,
    JobRepository,
)
from deadair.domain.entities.job import Job, JobStatus, StepStatus
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import VideoId


class JobRepositoryContractTests:
    """Shared behavioral contract for any JobRepository adapter. Subclass and
    provide a `repo` fixture returning a fresh adapter instance; every test
    below then runs against that adapter."""

    @pytest.fixture
    def repo(self) -> JobRepository:
        raise NotImplementedError

    def test_add_then_get_returns_equal_job(self, repo):
        job = Job.create(VideoId.new())
        repo.add(job)
        assert repo.get(job.id) == job

    def test_get_missing_returns_none(self, repo):
        assert repo.get(Job.create(VideoId.new()).id) is None

    def test_add_duplicate_id_raises_job_already_exists(self, repo):
        job = Job.create(VideoId.new())
        repo.add(job)
        with pytest.raises(JobAlreadyExistsError):
            repo.add(job)

    def test_update_persists_new_state(self, repo):
        job = Job.create(VideoId.new())
        repo.add(job)
        updated = job.with_step_updated(PipelineStep.EXTRACT_AUDIO, status=StepStatus.RUNNING)
        repo.update(updated)
        fetched = repo.get(job.id)
        assert fetched.status == JobStatus.RUNNING
        assert fetched.step_state(PipelineStep.EXTRACT_AUDIO).status == StepStatus.RUNNING

    def test_update_missing_job_raises_job_not_found(self, repo):
        job = Job.create(VideoId.new())
        with pytest.raises(JobNotFoundError):
            repo.update(job)

    def test_list_for_video_returns_only_that_videos_jobs_ordered_by_created_at(self, repo):
        video_a, video_b = VideoId.new(), VideoId.new()
        job_a1 = Job.create(video_a)
        job_a2 = Job.create(video_a)
        job_b1 = Job.create(video_b)
        for j in (job_a1, job_a2, job_b1):
            repo.add(j)

        result = repo.list_for_video(video_a)
        assert {j.id for j in result} == {job_a1.id, job_a2.id}
        assert [j.created_at for j in result] == sorted(j.created_at for j in result)

    def test_list_active_excludes_done_failed_cancelled(self, repo):
        pending_job = Job.create(VideoId.new())
        done_job = Job.create(VideoId.new())
        for step in PipelineStep:
            done_job = done_job.with_step_updated(step, status=StepStatus.DONE)
        cancelled_job = Job.create(VideoId.new()).cancel()

        repo.add(pending_job)
        repo.add(done_job)
        repo.add(cancelled_job)

        active_ids = {j.id for j in repo.list_active()}
        assert active_ids == {pending_job.id}
