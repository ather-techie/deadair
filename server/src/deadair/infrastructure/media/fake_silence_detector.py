from pathlib import Path

from deadair.application.ports.silence_detector import SilenceDetector
from deadair.domain.policies.silence_policy import SilenceDetectionConfig
from deadair.domain.value_objects.time_range import TimeRange


class FakeSilenceDetector(SilenceDetector):
    """Dev/test fake: reports no candidate silence gaps at all. Used until the
    real ffmpeg-silencedetect-backed adapter lands (M4)."""

    def detect_candidate_gaps(self, audio_path: Path, config: SilenceDetectionConfig) -> list[TimeRange]:
        return []
