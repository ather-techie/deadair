from deadair.application.ports.audio_extractor import AudioExtractionError
from deadair.application.use_cases.run_pipeline_job import _run
from deadair.config import Settings
from deadair.container import Container
from deadair.domain.entities.job import Job, JobStatus, StepStatus
from deadair.domain.entities.video import Video
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import VideoId
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

MVP_STEPS = (
    PipelineStep.EXTRACT_AUDIO,
    PipelineStep.TRANSCRIBE,
    PipelineStep.DETECT_SILENCE,
    PipelineStep.DETECT_FILLER,
    PipelineStep.BUILD_EDL,
    PipelineStep.RENDER,
)


class _RaisingAudioExtractor:
    def extract(self, source_path, config):
        raise AudioExtractionError("ffmpeg exploded")


def _make_container(tmp_path, **overrides) -> Container:
    settings = Settings(ffmpeg_binary_path=tmp_path / "ffmpeg", data_dir=tmp_path / "data")
    defaults = dict(
        settings=settings,
        job_repository=InMemoryJobRepository(),
        job_runner=InMemoryJobRunner(),
        video_repository=InMemoryVideoRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        progress_reporter=InMemoryProgressReporter(),
        audio_extractor=FakeAudioExtractor(tmp_path / "audio"),
        transcriber=FakeTranscriber(),
        silence_detector=FakeSilenceDetector(),
        video_renderer=FakeVideoRenderer(),
    )
    defaults.update(overrides)
    return Container(**defaults)


def _make_video(tmp_path) -> Video:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake video bytes")
    return Video(id=VideoId.new(), source_path=str(source), content_hash="hash", duration_seconds=2.0)


def test_happy_path_runs_all_steps_to_done(tmp_path):
    container = _make_container(tmp_path)
    video = _make_video(tmp_path)
    container.video_repository.add(video)
    job = Job.create(video.id, steps=MVP_STEPS)
    container.job_repository.add(job)

    _run(container, job.id)

    final = container.job_repository.get(job.id)
    assert final.status == JobStatus.DONE
    assert all(s.status == StepStatus.DONE for s in final.steps)


def test_progress_reported_during_transcription(tmp_path):
    container = _make_container(tmp_path)
    video = _make_video(tmp_path)
    container.video_repository.add(video)
    job = Job.create(video.id, steps=MVP_STEPS)
    container.job_repository.add(job)

    _run(container, job.id)

    assert container.progress_reporter.get(job.id, PipelineStep.TRANSCRIBE) is not None


def test_cache_hit_skips_recomputation_on_a_second_job_for_the_same_video(tmp_path):
    container = _make_container(tmp_path)
    video = _make_video(tmp_path)
    container.video_repository.add(video)
    job1 = Job.create(video.id, steps=MVP_STEPS)
    container.job_repository.add(job1)
    _run(container, job1.id)

    calls = []
    original_extract = container.audio_extractor.extract
    container.audio_extractor.extract = lambda *a, **kw: (calls.append(1), original_extract(*a, **kw))[1]

    job2 = Job.create(video.id, steps=MVP_STEPS)
    container.job_repository.add(job2)
    _run(container, job2.id)

    final = container.job_repository.get(job2.id)
    assert final.step_state(PipelineStep.EXTRACT_AUDIO).status == StepStatus.SKIPPED_CACHED
    assert calls == []


def test_port_failure_marks_job_failed_and_stops_downstream_steps(tmp_path):
    container = _make_container(tmp_path, audio_extractor=_RaisingAudioExtractor())
    video = _make_video(tmp_path)
    container.video_repository.add(video)
    job = Job.create(video.id, steps=MVP_STEPS)
    container.job_repository.add(job)

    _run(container, job.id)

    final = container.job_repository.get(job.id)
    assert final.status == JobStatus.FAILED
    assert final.step_state(PipelineStep.EXTRACT_AUDIO).status == StepStatus.FAILED
    assert final.step_state(PipelineStep.EXTRACT_AUDIO).error == "ffmpeg exploded"
    assert final.step_state(PipelineStep.TRANSCRIBE).status == StepStatus.PENDING
