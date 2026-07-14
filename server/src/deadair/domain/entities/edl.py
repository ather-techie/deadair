from dataclasses import dataclass

from deadair.domain.value_objects.ids import VideoId
from deadair.domain.value_objects.time_range import TimeRange


@dataclass(frozen=True, slots=True)
class EDL:
    video_id: VideoId
    keep_ranges: tuple[TimeRange, ...]
    total_duration: float

    def __post_init__(self) -> None:
        if self.total_duration < 0:
            raise ValueError("total_duration must be >= 0")
        prev_end = 0.0
        for r in self.keep_ranges:
            if r.start < 0 or r.end > self.total_duration:
                raise ValueError("keep range out of [0, total_duration] bounds")
            if r.start < prev_end:
                raise ValueError("keep_ranges must be sorted and non-overlapping")
            prev_end = r.end

    def cut_ranges(self) -> tuple[TimeRange, ...]:
        """Derived as the complement of keep_ranges in [0, total_duration].
        This is what makes 'keep + cut partitions the timeline, no gaps/overlaps'
        true BY CONSTRUCTION rather than by a separately-maintained invariant."""
        cuts: list[TimeRange] = []
        cursor = 0.0
        for k in self.keep_ranges:
            if k.start > cursor:
                cuts.append(TimeRange(cursor, k.start))
            cursor = k.end
        if cursor < self.total_duration:
            cuts.append(TimeRange(cursor, self.total_duration))
        return tuple(cuts)
