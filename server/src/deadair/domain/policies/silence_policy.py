from collections.abc import Sequence
from dataclasses import dataclass

from deadair.domain.value_objects.time_range import TimeRange


@dataclass(frozen=True, slots=True)
class SilenceDetectionConfig:
    noise_floor_db: float = -35.0
    min_silence_duration: float = 0.5


def filter_cuttable_silences(
    candidate_gaps: Sequence[TimeRange], config: SilenceDetectionConfig
) -> list[TimeRange]:
    """Given raw candidate silence gaps (produced by an infra silence detector,
    not yet implemented), keep only those long enough to be worth cutting."""
    return [g for g in candidate_gaps if g.duration >= config.min_silence_duration]
