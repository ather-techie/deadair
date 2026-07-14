from collections.abc import Callable
from typing import Any

import rq
from redis import Redis

from deadair.application.ports.job_runner import JobRunner


class RQJobRunner(JobRunner):
    """Enqueues work onto a real RQ queue. `func` must be a top-level,
    dotted-path-importable function (never a closure/bound method) -- a
    separate `rq worker` process imports it by dotted path and calls it with
    the given picklable args/kwargs (see JobRunner's docstring). Takes an
    already-constructed Redis connection (real or fake) rather than a URL,
    so it stays trivially testable against fakeredis."""

    def __init__(self, connection: Redis, queue_name: str = "deadair", job_timeout_seconds: int = 3600):
        self._connection = connection
        self._queue = rq.Queue(queue_name, connection=connection)
        # RQ's own default (180s) is too short for a full extract+transcribe+
        # render pipeline on anything but a very short video.
        self._job_timeout_seconds = job_timeout_seconds

    def enqueue(self, func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> str:
        job = self._queue.enqueue(func, *args, job_timeout=self._job_timeout_seconds, **kwargs)
        return job.id

    def cancel(self, execution_id: str) -> None:
        try:
            job = rq.job.Job.fetch(execution_id, connection=self._connection)
        except rq.exceptions.NoSuchJobError:
            return
        job.cancel()
