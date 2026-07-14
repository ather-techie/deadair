from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from deadair.domain.entities.transcript import Transcript
from deadair.domain.pipeline.step_configs import TranscribeConfig
from deadair.domain.value_objects.ids import VideoId


class TranscriptionError(Exception):
    pass


class Transcriber(ABC):
    """Produces a word-level Transcript from an extracted audio file."""

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        video_id: VideoId,
        config: TranscribeConfig,
        on_progress: Callable[[float], None] | None = None,
    ) -> Transcript:
        """Runs the configured model against audio_path. Word-level timestamps
        are required — filler_policy and edl_builder both key off
        Word.start/end. Raises TranscriptionError on failure. on_progress, if
        given, is called with a fraction in [0, 1] as transcription proceeds."""
