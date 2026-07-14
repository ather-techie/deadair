from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TimeRange:
    """A half-open interval [start, end) in seconds."""

    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("start must be >= 0")
        if self.end < self.start:
            raise ValueError("end must be >= start")

    @property
    def duration(self) -> float:
        return self.end - self.start

    def overlaps(self, other: "TimeRange") -> bool:
        return self.start < other.end and other.start < self.end

    def touches(self, other: "TimeRange") -> bool:
        """True if overlapping OR contiguous (no gap between them)."""
        return self.start <= other.end and other.start <= self.end
