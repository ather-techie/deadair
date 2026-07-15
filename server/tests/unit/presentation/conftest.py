import pytest
from fastapi.testclient import TestClient

from deadair.config import Settings
from deadair.container import Container
from deadair.infrastructure.jobs.in_memory_job_runner import InMemoryJobRunner
from deadair.infrastructure.media.fake_audio_extractor import FakeAudioExtractor
from deadair.infrastructure.media.fake_silence_detector import FakeSilenceDetector
from deadair.infrastructure.media.fake_transcriber import FakeTranscriber
from deadair.infrastructure.media.fake_video_renderer import FakeVideoRenderer
from deadair.infrastructure.persistence.in_memory.artifact_repository_memory import (
    InMemoryArtifactRepository,
)
from deadair.infrastructure.persistence.in_memory.job_repository_memory import InMemoryJobRepository
from deadair.infrastructure.persistence.in_memory.video_repository_memory import InMemoryVideoRepository
from deadair.infrastructure.progress.in_memory_progress_reporter import InMemoryProgressReporter
from deadair.infrastructure.progress.in_memory_transcript_segment_sink import InMemoryTranscriptSegmentSink
from deadair.presentation.api.app import create_app


@pytest.fixture
def container(tmp_path, monkeypatch) -> Container:
    settings = Settings(ffmpeg_binary_path=tmp_path / "ffmpeg", data_dir=tmp_path / "data")
    fake_container = Container(
        settings=settings,
        job_repository=InMemoryJobRepository(),
        job_runner=InMemoryJobRunner(),
        video_repository=InMemoryVideoRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        progress_reporter=InMemoryProgressReporter(),
        transcript_segment_sink=InMemoryTranscriptSegmentSink(),
        audio_extractor=FakeAudioExtractor(tmp_path / "audio"),
        transcriber=FakeTranscriber(),
        silence_detector=FakeSilenceDetector(),
        video_renderer=FakeVideoRenderer(),
    )
    # run_pipeline_job (invoked synchronously in-process by InMemoryJobRunner)
    # calls build_container() itself with no args -- that's the real
    # RQ-compatible contract (top-level function + primitive args only, see
    # JobRunner's docstring). Patch its build_container reference so the
    # pipeline actually runs against this same all-fake container rather than
    # loading real Settings/ffmpeg adapters from the environment.
    monkeypatch.setattr(
        "deadair.application.use_cases.run_pipeline_job.build_container",
        lambda settings=None: fake_container,
    )
    return fake_container


@pytest.fixture
def client(container: Container) -> TestClient:
    return TestClient(create_app(container))
