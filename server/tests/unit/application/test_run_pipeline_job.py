from deadair.application.ports.audio_extractor import AudioExtractionError
from deadair.application.ports.transcriber import TranscriptionError
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
from deadair.infrastructure.progress.in_memory_transcript_segment_sink import InMemoryTranscriptSegmentSink

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


class _RaisingTranscriber:
    def transcribe(self, audio_path, video_id, config, on_progress=None, on_segment=None):
        raise TranscriptionError("whisper exploded")


def _make_container(tmp_path, **overrides) -> Container:
    settings = Settings(ffmpeg_binary_path=tmp_path / "ffmpeg", data_dir=tmp_path / "data")
    defaults = dict(
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


def test_transcribe_segments_are_appended_to_the_segment_sink_incrementally(tmp_path):
    container = _make_container(tmp_path)
    video = _make_video(tmp_path)
    container.video_repository.add(video)
    job = Job.create(video.id, steps=MVP_STEPS)
    container.job_repository.add(job)

    _run(container, job.id)

    segments = container.transcript_segment_sink.list_after(job.id, after_index=-1)
    assert [i for i, _ in segments] == [0]
    assert segments[0][1].text == "um hello world"


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


def test_excluding_a_detector_step_still_builds_and_renders_with_findings_for_the_other(tmp_path):
    container = _make_container(tmp_path)
    video = _make_video(tmp_path)
    container.video_repository.add(video)
    steps = (
        PipelineStep.EXTRACT_AUDIO,
        PipelineStep.DETECT_SILENCE,
        PipelineStep.BUILD_EDL,
        PipelineStep.RENDER,
    )
    job = Job.create(video.id, steps=steps)
    container.job_repository.add(job)

    _run(container, job.id)

    final = container.job_repository.get(job.id)
    assert final.status == JobStatus.DONE
    assert all(s.status == StepStatus.DONE for s in final.steps)
    silence_findings = final.step_state(PipelineStep.DETECT_SILENCE).findings
    assert silence_findings is not None
    assert silence_findings["cuts"] >= 0
    assert silence_findings["seconds_removed"] >= 0


def test_port_failure_cascades_to_every_dependent_step(tmp_path):
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
    # every other MVP step transitively depends on EXTRACT_AUDIO, so all cascade-fail
    # rather than being left PENDING
    for step in (
        PipelineStep.TRANSCRIBE,
        PipelineStep.DETECT_SILENCE,
        PipelineStep.DETECT_FILLER,
        PipelineStep.BUILD_EDL,
        PipelineStep.RENDER,
    ):
        assert final.step_state(step).status == StepStatus.FAILED


def test_transcribe_failure_does_not_block_independent_render_when_filler_removal_not_selected(tmp_path):
    container = _make_container(tmp_path, transcriber=_RaisingTranscriber())
    video = _make_video(tmp_path)
    container.video_repository.add(video)
    steps = (
        PipelineStep.EXTRACT_AUDIO,
        PipelineStep.TRANSCRIBE,  # requested only to show the transcript, not for filler removal
        PipelineStep.DETECT_SILENCE,
        PipelineStep.BUILD_EDL,
        PipelineStep.RENDER,
    )
    job = Job.create(video.id, steps=steps)
    container.job_repository.add(job)

    _run(container, job.id)

    final = container.job_repository.get(job.id)
    assert final.status == JobStatus.FAILED
    assert final.step_state(PipelineStep.TRANSCRIBE).status == StepStatus.FAILED
    # BUILD_EDL only depends on DETECT_SILENCE here (DETECT_FILLER wasn't selected), so
    # the render still completes on silence-only cuts despite the transcript failing
    assert final.step_state(PipelineStep.DETECT_SILENCE).status == StepStatus.DONE
    assert final.step_state(PipelineStep.BUILD_EDL).status == StepStatus.DONE
    assert final.step_state(PipelineStep.RENDER).status == StepStatus.DONE


def test_transcribe_failure_cascades_to_render_when_filler_removal_selected(tmp_path):
    container = _make_container(tmp_path, transcriber=_RaisingTranscriber())
    video = _make_video(tmp_path)
    container.video_repository.add(video)
    job = Job.create(video.id, steps=MVP_STEPS)
    container.job_repository.add(job)

    _run(container, job.id)

    final = container.job_repository.get(job.id)
    assert final.status == JobStatus.FAILED
    assert final.step_state(PipelineStep.TRANSCRIBE).status == StepStatus.FAILED
    assert final.step_state(PipelineStep.DETECT_FILLER).status == StepStatus.FAILED
    assert final.step_state(PipelineStep.BUILD_EDL).status == StepStatus.FAILED
    assert final.step_state(PipelineStep.RENDER).status == StepStatus.FAILED
    # DETECT_SILENCE is independent of TRANSCRIBE, so it still completes
    assert final.step_state(PipelineStep.DETECT_SILENCE).status == StepStatus.DONE
