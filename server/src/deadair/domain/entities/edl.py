from dataclasses import dataclass

from deadair.domain.value_objects.ids import VideoId
from deadair.domain.value_objects.time_range import TimeRange, complement


@dataclass(frozen=True, slots=True)
class EdlSegment:
    """A range of the source video present in the output. rate=1.0 plays at
    normal speed (today's "keep" ranges); rate>1.0 is a range that would
    otherwise be cut but is instead sped up and retained."""

    range: TimeRange
    rate: float = 1.0

    def __post_init__(self) -> None:
        if self.rate <= 0:
            raise ValueError("rate must be > 0")


@dataclass(frozen=True, slots=True)
class EDL:
    video_id: VideoId
    segments: tuple[EdlSegment, ...]
    total_duration: float

    def __post_init__(self) -> None:
        if self.total_duration < 0:
            raise ValueError("total_duration must be >= 0")
        prev_end = 0.0
        for s in self.segments:
            r = s.range
            if r.start < 0 or r.end > self.total_duration:
                raise ValueError("segment range out of [0, total_duration] bounds")
            if r.start < prev_end:
                raise ValueError("segments must be sorted and non-overlapping")
            prev_end = r.end

    def cut_ranges(self) -> tuple[TimeRange, ...]:
        """Derived as the complement of segment ranges in [0, total_duration]
        -- the parts of the source genuinely absent from the output. This is
        what makes 'present + cut partitions the timeline, no gaps/overlaps'
        true BY CONSTRUCTION rather than by a separately-maintained invariant."""
        return tuple(complement([s.range for s in self.segments], self.total_duration))
