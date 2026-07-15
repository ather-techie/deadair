"""RQ worker entrypoint: `python -m deadair.worker`.

Runs against the same queue name / Redis URL as the API process's
RQJobRunner (Settings.rq_queue_name / Settings.redis_url), so jobs enqueued
by the API get picked up here. Each job invocation (`run_pipeline_job`)
rebuilds its own Container from this process's environment -- see
run_pipeline_job's docstring.
"""

import sys

from redis import Redis
from rq import SimpleWorker, Worker
from rq.timeouts import TimerDeathPenalty

from deadair.config import load_settings
from deadair.logging_config import configure_logging


class _WindowsSimpleWorker(SimpleWorker):
    # SimpleWorker's (and Worker's) default death_penalty_class enforces job
    # timeouts via SIGALRM, which doesn't exist on Windows -- TimerDeathPenalty
    # is RQ's threading+ctypes-based alternative for platforms without it.
    death_penalty_class = TimerDeathPenalty


def main() -> None:
    settings = load_settings()
    configure_logging(settings)
    connection = Redis.from_url(settings.redis_url)
    # rq.Worker also forks a subprocess per job via os.fork(), which doesn't
    # exist on Windows -- SimpleWorker runs jobs in-process instead, at the
    # cost of the extra crash isolation forking provides.
    worker_cls = _WindowsSimpleWorker if sys.platform == "win32" else Worker
    worker_cls([settings.rq_queue_name], connection=connection).work()


if __name__ == "__main__":
    main()
