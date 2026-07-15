from abc import ABC, abstractmethod
from pathlib import Path

from deadair.domain.entities.edl import EDL
from deadair.domain.pipeline.step_configs import RenderConfig


class RenderError(Exception):
    pass


class VideoRenderer(ABC):
    """Cuts a source video down to an EDL's segments and re-encodes it."""

    @abstractmethod
    def render(self, source_path: Path, edl: EDL, config: RenderConfig, output_path: Path) -> Path:
        """Writes the rendered cut to output_path and returns it. Raises
        RenderError on failure."""
