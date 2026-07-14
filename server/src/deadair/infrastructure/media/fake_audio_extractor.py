import shutil
import uuid
from pathlib import Path

from deadair.application.ports.audio_extractor import AudioExtractor
from deadair.domain.pipeline.step_configs import ExtractAudioConfig


class FakeAudioExtractor(AudioExtractor):
    """Dev/test fake: doesn't decode audio at all, just copies the source
    file to a .wav-named path so the rest of the pipeline has something to
    operate on. Used until the real ffmpeg-backed adapter lands (M4)."""

    def __init__(self, work_dir: Path):
        self._work_dir = Path(work_dir)

    def extract(self, source_path: Path, config: ExtractAudioConfig) -> Path:
        self._work_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._work_dir / f"{Path(source_path).stem}-{uuid.uuid4().hex}.wav"
        shutil.copy(source_path, output_path)
        return output_path
