from collections.abc import Callable
from pathlib import Path

from deadair.application.ports.transcriber import Transcriber
from deadair.domain.entities.transcript import Segment, Transcript, Word
from deadair.domain.pipeline.step_configs import TranscribeConfig
from deadair.domain.value_objects.ids import VideoId


class FakeTranscriber(Transcriber):
    """Dev/test fake: returns a canned transcript instead of running Whisper.
    Used until the real faster-whisper-backed adapter lands (M5)."""

    def transcribe(
        self,
        audio_path: Path,
        video_id: VideoId,
        config: TranscribeConfig,
        on_progress: Callable[[float], None] | None = None,
    ) -> Transcript:
        if on_progress:
            on_progress(1.0)
        words = (
            Word(text="um", start=0.0, end=0.4, confidence=0.9),
            Word(text="hello", start=0.4, end=0.9, confidence=0.98),
            Word(text="world", start=0.9, end=1.3, confidence=0.97),
        )
        segment = Segment(words=words, start=0.0, end=1.3, text="um hello world")
        return Transcript(video_id=video_id, segments=(segment,), language=config.language or "en")
