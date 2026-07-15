from collections.abc import Sequence
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


def complement(ranges: Sequence[TimeRange], total: float) -> list[TimeRange]:
    """Gaps not covered by `ranges` within [0, total]. `ranges` need not be
    sorted; used symmetrically to derive keep-from-cut and cut-from-keep."""
    ordered = sorted(ranges, key=lambda r: r.start)
    gaps: list[TimeRange] = []
    cursor = 0.0
    for r in ordered:
        r_start, r_end = max(0.0, min(r.start, total)), max(0.0, min(r.end, total))
        if r_start > cursor:
            gaps.append(TimeRange(cursor, r_start))
        cursor = max(cursor, r_end)
    if cursor < total:
        gaps.append(TimeRange(cursor, total))
    return gaps
