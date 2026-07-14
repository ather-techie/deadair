from abc import ABC, abstractmethod
from pathlib import Path

from deadair.domain.pipeline.step_configs import ExtractAudioConfig


class AudioExtractionError(Exception):
    pass


class AudioExtractor(ABC):
    """Extracts a mono/resampled audio track from a source video file."""

    @abstractmethod
    def extract(self, source_path: Path, config: ExtractAudioConfig) -> Path:
        """Writes a WAV file per config (sample_rate, channels) and returns its
        path. Raises AudioExtractionError on failure."""
