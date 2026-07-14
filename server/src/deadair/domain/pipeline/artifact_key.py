from dataclasses import dataclass

from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import VideoId


@dataclass(frozen=True, slots=True)
class ArtifactKey:
    video_id: VideoId
    step: PipelineStep
    config_hash: str
