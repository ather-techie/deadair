from collections.abc import Sequence
from dataclasses import dataclass

from deadair.domain.entities.edl import EDL, EdlSegment
from deadair.domain.value_objects.ids import VideoId
from deadair.domain.value_objects.time_range import TimeRange, complement


@dataclass(frozen=True, slots=True)
class BuildEdlConfig:
    padding_seconds: float = 0.15
    min_keep_duration: float = 0.3
    speed_multiplier: float | None = None
    """When set, cut ranges are retained and sped up by this factor instead
    of being removed entirely. None (default) reproduces the plain hard-cut
    behavior."""


def merge_overlapping(ranges: Sequence[TimeRange]) -> list[TimeRange]:
    if not ranges:
        return []
    ordered = sorted(ranges, key=lambda r: r.start)
    merged = [ordered[0]]
    for r in ordered[1:]:
        last = merged[-1]
        if r.start <= last.end:
            merged[-1] = TimeRange(last.start, max(last.end, r.end))
        else:
            merged.append(r)
    return merged


def _pad_cut(c: TimeRange, padding: float) -> TimeRange:
    """Shrink a cut range inward by `padding` on each side so we don't clip
    speech right at the boundary. If the range is too short to survive full
    padding, cut it as-is rather than dropping the cut entirely."""
    new_start, new_end = c.start + padding, c.end - padding
    return TimeRange(new_start, new_end) if new_end > new_start else c


def build_edl(
    video_id: VideoId,
    video_duration: float,
    silence_cut_ranges: Sequence[TimeRange],
    filler_cut_ranges: Sequence[TimeRange],
    config: BuildEdlConfig,
) -> EDL:
    """
    1. Union silence + filler candidate cut ranges, merging overlaps.
    2. Pad (shrink) each merged cut inward so a buffer of speech survives at
       each edge; a cut too short to fully absorb the padding is cut as-is
       instead of being dropped.
    3. Derive keep ranges as the complement of the padded cuts over
       [0, video_duration].
    4. Drop any keep range shorter than min_keep_duration — dropping it (not
       "merging" it) is sufficient because EDL.cut_ranges() is *always*
       derived as the complement of the segments' ranges, so a dropped keep
       range automatically becomes part of a cut with no separate merge logic.
    5. If config.speed_multiplier is set, the gaps between kept ranges (what
       would otherwise be pure cuts) are retained as segments played back at
       that rate instead of being dropped.
    6. Construct EDL — its __post_init__ enforces sorted/non-overlapping/
       in-bounds segment ranges, which combined with the complement-derivation
       of cut_ranges() guarantees the "no gaps, no overlaps, full partition"
       property by construction.
    """
    merged_cuts = merge_overlapping(list(silence_cut_ranges) + list(filler_cut_ranges))
    padded_cuts = [_pad_cut(c, config.padding_seconds) for c in merged_cuts]
    keep = complement(padded_cuts, video_duration)
    keep = [k for k in keep if k.duration >= config.min_keep_duration]

    segments = [EdlSegment(range=k, rate=1.0) for k in keep]
    if config.speed_multiplier is not None:
        gaps = complement(keep, video_duration)
        segments += [EdlSegment(range=g, rate=config.speed_multiplier) for g in gaps if g.duration > 0]
        segments.sort(key=lambda s: s.range.start)

    return EDL(video_id=video_id, segments=tuple(segments), total_duration=video_duration)


def map_to_result_time(t: float, segments: Sequence[EdlSegment]) -> float:
    """Maps a timestamp on the original timeline to where it lands on the
    trimmed-output timeline, given the EDL's segments (sorted, non-overlapping
    by construction). A point inside a segment lands proportionally into its
    (possibly sped-up) output duration; a point in a genuine gap (nothing
    covers it) clamps forward to the elapsed output-duration at that point."""
    elapsed = 0.0
    for seg in segments:
        r = seg.range
        if t <= r.start:
            return elapsed
        if t < r.end:
            return elapsed + (t - r.start) / seg.rate
        elapsed += r.duration / seg.rate
    return elapsed
