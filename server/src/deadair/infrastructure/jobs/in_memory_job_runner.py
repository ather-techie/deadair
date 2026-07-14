import itertools
from collections.abc import Callable
from typing import Any

from deadair.application.ports.job_runner import JobRunner


class InMemoryJobRunner(JobRunner):
    """Synchronous fake: calls func(*args, **kwargs) immediately in-process."""

    def __init__(self) -> None:
        self._results: dict[str, Any] = {}
        self._counter = itertools.count(1)

    def enqueue(self, func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> str:
        execution_id = str(next(self._counter))
        self._results[execution_id] = func(*args, **kwargs)
        return execution_id

    def cancel(self, execution_id: str) -> None:
        self._results.pop(execution_id, None)
