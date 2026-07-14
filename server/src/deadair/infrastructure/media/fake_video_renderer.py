import shutil
from pathlib import Path

from deadair.application.ports.video_renderer import VideoRenderer
from deadair.domain.entities.edl import EDL
from deadair.domain.pipeline.step_configs import RenderConfig


class FakeVideoRenderer(VideoRenderer):
    """Dev/test fake: copies the source file unmodified as the 'rendered'
    output rather than actually cutting it. Used until the real ffmpeg-backed
    adapter lands (M6)."""

    def render(self, source_path: Path, edl: EDL, config: RenderConfig, output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source_path, output_path)
        return output_path
