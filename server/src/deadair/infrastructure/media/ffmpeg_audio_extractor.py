import uuid
from pathlib import Path

from deadair.application.ports.audio_extractor import AudioExtractionError, AudioExtractor
from deadair.domain.pipeline.step_configs import ExtractAudioConfig
from deadair.infrastructure.media.ffmpeg_runner import FfmpegInvocationError, run_ffmpeg


class FfmpegAudioExtractor(AudioExtractor):
    def __init__(self, ffmpeg_binary_path: Path, work_dir: Path):
        self._ffmpeg_binary_path = Path(ffmpeg_binary_path)
        self._work_dir = Path(work_dir)

    def extract(self, source_path: Path, config: ExtractAudioConfig) -> Path:
        self._work_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._work_dir / f"{Path(source_path).stem}-{uuid.uuid4().hex}.wav"
        try:
            run_ffmpeg(
                self._ffmpeg_binary_path,
                [
                    "-y",
                    "-i",
                    str(source_path),
                    "-vn",
                    "-ar",
                    str(config.sample_rate),
                    "-ac",
                    str(config.channels),
                    str(output_path),
                ],
            )
        except FfmpegInvocationError as exc:
            raise AudioExtractionError(str(exc)) from exc
        return output_path
