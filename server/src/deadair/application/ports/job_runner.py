from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class JobRunner(ABC):
    """Enqueues pipeline work for async execution. Designed around RQ's
    execution model: callers enqueue a *reference* to a top-level, picklable
    function plus plain picklable args/kwargs — not closures or bound methods
    holding unpicklable state — because a real RQ worker is a separate
    process that imports the function by dotted path and calls it. Milestone
    1-2 ships only this ABC plus an in-memory synchronous fake
    (infrastructure/jobs/in_memory_job_runner.py); the real RQ+Redis adapter
    is a later milestone."""

    @abstractmethod
    def enqueue(self, func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> str:
        """Returns an opaque runner-assigned execution id."""

    @abstractmethod
    def cancel(self, execution_id: str) -> None:
        """Best-effort; no-op if already finished/unknown."""
