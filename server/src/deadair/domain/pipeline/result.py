from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    artifact_ref: T

    def is_ok(self) -> bool:
        return True

    def is_failure(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class Failure:
    reason: str
    retryable: bool = True

    def is_ok(self) -> bool:
        return False

    def is_failure(self) -> bool:
        return True


StepResult: TypeAlias = "Ok[T] | Failure"
