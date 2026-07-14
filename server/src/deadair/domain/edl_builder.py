from collections.abc import Sequence
from dataclasses import dataclass

from deadair.domain.entities.edl import EDL
from deadair.domain.value_objects.ids import VideoId
from deadair.domain.value_objects.time_range import TimeRange


@dataclass(frozen=True, slots=True)
class BuildEdlConfig:
    padding_seconds: float = 0.15
    min_keep_duration: float = 0.3


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


def _pad_cut(c: TimeRange, padding: float) -> TimeRange | None:
    """Shrink a cut range inward by `padding` on each side so we don't clip
    speech right at the boundary. If the range is too short to survive
    padding, it's not a cut at all (returns None -> fully kept)."""
    new_start, new_end = c.start + padding, c.end - padding
    return TimeRange(new_start, new_end) if new_end > new_start else None


def _complement(cuts: Sequence[TimeRange], total: float) -> list[TimeRange]:
    cuts_sorted = sorted(cuts, key=lambda r: r.start)
    keep: list[TimeRange] = []
    cursor = 0.0
    for c in cuts_sorted:
        c_start, c_end = max(0.0, min(c.start, total)), max(0.0, min(c.end, total))
        if c_start > cursor:
            keep.append(TimeRange(cursor, c_start))
        cursor = max(cursor, c_end)
    if cursor < total:
        keep.append(TimeRange(cursor, total))
    return keep


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
       each edge.
    3. Derive keep ranges as the complement of the padded cuts over
       [0, video_duration].
    4. Drop any keep range shorter than min_keep_duration — dropping it (not
       "merging" it) is sufficient because EDL.cut_ranges() is *always*
       derived as the complement of keep_ranges, so a dropped keep range
       automatically becomes part of a cut with no separate merge logic.
    5. Construct EDL — its __post_init__ enforces sorted/non-overlapping/
       in-bounds keep_ranges, which combined with the complement-derivation of
       cut_ranges() guarantees the "no gaps, no overlaps, full partition"
       property by construction.
    """
    merged_cuts = merge_overlapping(list(silence_cut_ranges) + list(filler_cut_ranges))
    padded_cuts = [pc for c in merged_cuts if (pc := _pad_cut(c, config.padding_seconds)) is not None]
    keep = _complement(padded_cuts, video_duration)
    keep = [k for k in keep if k.duration >= config.min_keep_duration]
    return EDL(video_id=video_id, keep_ranges=tuple(keep), total_duration=video_duration)
