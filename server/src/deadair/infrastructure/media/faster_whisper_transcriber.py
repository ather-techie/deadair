from collections.abc import Callable
from pathlib import Path

from faster_whisper import WhisperModel

from deadair.application.ports.transcriber import Transcriber, TranscriptionError
from deadair.domain.entities.transcript import Segment, Transcript, Word
from deadair.domain.pipeline.step_configs import TranscribeConfig
from deadair.domain.value_objects.ids import VideoId


class FasterWhisperTranscriber(Transcriber):
    """Loads a WhisperModel lazily and caches it for the adapter instance's
    lifetime (a worker process, in production) since model load is
    expensive. Reloads only if a job requests a different model_name."""

    def __init__(self, device: str, compute_type: str):
        self._device = device
        self._compute_type = compute_type
        self._model_name: str | None = None
        self._model: WhisperModel | None = None

    def _get_model(self, model_name: str) -> WhisperModel:
        if self._model is None or self._model_name != model_name:
            self._model = WhisperModel(model_name, device=self._device, compute_type=self._compute_type)
            self._model_name = model_name
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        video_id: VideoId,
        config: TranscribeConfig,
        on_progress: Callable[[float], None] | None = None,
        on_segment: Callable[[Segment], None] | None = None,
    ) -> Transcript:
        try:
            model = self._get_model(config.model_name)
            segments_iter, info = model.transcribe(
                str(audio_path),
                language=config.language,
                word_timestamps=True,
                condition_on_previous_text=config.condition_on_previous_text,
                vad_filter=config.vad_filter,
                initial_prompt=config.initial_prompt,
            )
            total_duration = info.duration or 0.0
            segments = []
            for seg in segments_iter:
                words = tuple(
                    Word(text=w.word.strip(), start=w.start, end=w.end, confidence=w.probability)
                    for w in (seg.words or [])
                )
                segment = Segment(words=words, start=seg.start, end=seg.end, text=seg.text.strip())
                segments.append(segment)
                if on_segment:
                    on_segment(segment)
                if on_progress and total_duration > 0:
                    on_progress(min(seg.end / total_duration, 1.0))
        except Exception as exc:
            raise TranscriptionError(str(exc)) from exc

        if on_progress:
            on_progress(1.0)
        return Transcript(video_id=video_id, segments=tuple(segments), language=info.language)
