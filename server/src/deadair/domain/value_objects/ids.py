import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _Id:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("id value must not be empty")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class VideoId(_Id):
    @staticmethod
    def new() -> "VideoId":
        return VideoId(str(uuid.uuid4()))


@dataclass(frozen=True, slots=True)
class JobId(_Id):
    @staticmethod
    def new() -> "JobId":
        return JobId(str(uuid.uuid4()))


@dataclass(frozen=True, slots=True)
class TranscriptId(_Id):
    @staticmethod
    def new() -> "TranscriptId":
        return TranscriptId(str(uuid.uuid4()))


@dataclass(frozen=True, slots=True)
class EdlId(_Id):
    @staticmethod
    def new() -> "EdlId":
        return EdlId(str(uuid.uuid4()))
