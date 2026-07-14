from abc import ABC, abstractmethod
from pathlib import Path

from deadair.domain.policies.silence_policy import SilenceDetectionConfig
from deadair.domain.value_objects.time_range import TimeRange


class SilenceDetectionError(Exception):
    pass


class SilenceDetector(ABC):
    """Analyzes an audio file for silent gaps. Returns raw candidate gaps —
    it does NOT apply the min_silence_duration filter itself; that decision
    stays with domain.policies.silence_policy.filter_cuttable_silences, which
    the caller applies afterward."""

    @abstractmethod
    def detect_candidate_gaps(self, audio_path: Path, config: SilenceDetectionConfig) -> list[TimeRange]:
        """Raises SilenceDetectionError on failure."""
