import fakeredis
import rq

from deadair.infrastructure.jobs.rq_job_runner import RQJobRunner


def _sample_job(x: int, y: int) -> int:
    return x + y


def test_enqueue_returns_an_execution_id_for_a_queued_job():
    connection = fakeredis.FakeStrictRedis()
    runner = RQJobRunner(connection, queue_name="test-queue")

    execution_id = runner.enqueue(_sample_job, 2, 3)

    job = rq.job.Job.fetch(execution_id, connection=connection)
    assert job.is_queued
    assert job.args == (2, 3)


def test_cancel_marks_a_queued_job_as_cancelled():
    connection = fakeredis.FakeStrictRedis()
    runner = RQJobRunner(connection, queue_name="test-queue")
    execution_id = runner.enqueue(_sample_job, 2, 3)

    runner.cancel(execution_id)

    job = rq.job.Job.fetch(execution_id, connection=connection)
    assert job.is_canceled


def test_cancel_unknown_execution_id_is_a_noop():
    connection = fakeredis.FakeStrictRedis()
    runner = RQJobRunner(connection, queue_name="test-queue")

    runner.cancel("does-not-exist")
