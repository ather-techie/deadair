import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count
from pathlib import Path

from deadair.application.ports.audio_extractor import AudioExtractionError
from deadair.application.ports.silence_detector import SilenceDetectionError
from deadair.application.ports.transcriber import TranscriptionError
from deadair.application.ports.video_renderer import RenderError
from deadair.container import Container, build_container
from deadair.domain.edl_builder import BuildEdlConfig, build_edl
from deadair.domain.entities.edl import EDL, EdlSegment
from deadair.domain.entities.job import InvalidJobTransitionError, Job, JobStatus, StepStatus
from deadair.domain.entities.transcript import Segment, Transcript, Word
from deadair.domain.entities.video import Video
from deadair.domain.pipeline.artifact_key import ArtifactKey
from deadair.domain.pipeline.config_hash import compute_config_hash
from deadair.domain.pipeline.result import Failure
from deadair.domain.pipeline.step import STEP_DEPENDENCIES, PipelineStep
from deadair.domain.pipeline.step_configs import ExtractAudioConfig, RenderConfig, TranscribeConfig
from deadair.domain.policies.filler_policy import (
    FillerWordConfig,
    filler_words_to_ranges,
    find_filler_words,
)
from deadair.domain.policies.silence_policy import SilenceDetectionConfig, filter_cuttable_silences
from deadair.domain.value_objects.ids import JobId, VideoId
from deadair.domain.value_objects.time_range import TimeRange


def _step_configs_for(job: Job) -> dict[PipelineStep, object]:
    silence_kwargs = {}
    if job.noise_floor_db is not None:
        silence_kwargs["noise_floor_db"] = job.noise_floor_db
    if job.min_silence_duration is not None:
        silence_kwargs["min_silence_duration"] = job.min_silence_duration

    filler_kwargs = {}
    if job.filler_words is not None:
        filler_kwargs["words"] = job.filler_words
    if job.filler_case_sensitive is not None:
        filler_kwargs["case_sensitive"] = job.filler_case_sensitive

    edl_kwargs = {"speed_multiplier": job.speed_multiplier}
    if job.padding_seconds is not None:
        edl_kwargs["padding_seconds"] = job.padding_seconds
    if job.min_keep_duration is not None:
        edl_kwargs["min_keep_duration"] = job.min_keep_duration

    return {
        PipelineStep.EXTRACT_AUDIO: ExtractAudioConfig(),
        PipelineStep.TRANSCRIBE: TranscribeConfig(),
        PipelineStep.DETECT_SILENCE: SilenceDetectionConfig(**silence_kwargs),
        PipelineStep.DETECT_FILLER: FillerWordConfig(**filler_kwargs),
        PipelineStep.BUILD_EDL: BuildEdlConfig(**edl_kwargs),
        PipelineStep.RENDER: RenderConfig(),
    }


_TERMINAL_JOB_STATUSES = (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED)
_PORT_ERRORS = (AudioExtractionError, TranscriptionError, SilenceDetectionError, RenderError)
_SKIPPED_STEP_HASH = "skipped"  # sentinel for a dependency the job's step list excludes entirely


@dataclass
class _State:
    audio_path: Path | None = None
    transcript: Transcript | None = None
    silence_cut_ranges: list[TimeRange] = field(default_factory=list)
    filler_cut_ranges: list[TimeRange] = field(default_factory=list)
    edl: EDL | None = None
    rendered_path: Path | None = None


def _ranges_to_json(ranges: list[TimeRange]) -> bytes:
    return json.dumps([[r.start, r.end] for r in ranges]).encode("utf-8")


def _json_to_ranges(payload: bytes) -> list[TimeRange]:
    return [TimeRange(start, end) for start, end in json.loads(payload)]


def _transcript_to_json(transcript: Transcript) -> bytes:
    return json.dumps(
        {
            "language": transcript.language,
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "words": [
                        {"text": w.text, "start": w.start, "end": w.end, "confidence": w.confidence}
                        for w in seg.words
                    ],
                }
                for seg in transcript.segments
            ],
        }
    ).encode("utf-8")


def _json_to_transcript(payload: bytes, video_id: VideoId) -> Transcript:
    data = json.loads(payload)
    segments = tuple(
        Segment(
            words=tuple(Word(**w) for w in seg["words"]),
            start=seg["start"],
            end=seg["end"],
            text=seg["text"],
        )
        for seg in data["segments"]
    )
    return Transcript(video_id=video_id, segments=segments, language=data["language"])


def _edl_to_json(edl: EDL) -> bytes:
    return json.dumps(
        {
            "total_duration": edl.total_duration,
            "segments": [[s.range.start, s.range.end, s.rate] for s in edl.segments],
        }
    ).encode("utf-8")


def _json_to_edl(payload: bytes, video_id: VideoId) -> EDL:
    data = json.loads(payload)
    segments = tuple(EdlSegment(range=TimeRange(start, end), rate=rate) for start, end, rate in data["segments"])
    return EDL(video_id=video_id, segments=segments, total_duration=data["total_duration"])


def _serialize(step: PipelineStep, state: _State) -> bytes:
    if step is PipelineStep.EXTRACT_AUDIO:
        return json.dumps({"audio_path": str(state.audio_path)}).encode("utf-8")
    if step is PipelineStep.TRANSCRIBE:
        return _transcript_to_json(state.transcript)
    if step is PipelineStep.DETECT_SILENCE:
        return _ranges_to_json(state.silence_cut_ranges)
    if step is PipelineStep.DETECT_FILLER:
        return _ranges_to_json(state.filler_cut_ranges)
    if step is PipelineStep.BUILD_EDL:
        return _edl_to_json(state.edl)
    if step is PipelineStep.RENDER:
        return json.dumps({"output_path": str(state.rendered_path)}).encode("utf-8")
    raise ValueError(f"unsupported step: {step}")


def _apply_cached(step: PipelineStep, payload: bytes, video_id: VideoId, state: _State) -> None:
    if step is PipelineStep.EXTRACT_AUDIO:
        state.audio_path = Path(json.loads(payload)["audio_path"])
    elif step is PipelineStep.TRANSCRIBE:
        state.transcript = _json_to_transcript(payload, video_id)
    elif step is PipelineStep.DETECT_SILENCE:
        state.silence_cut_ranges = _json_to_ranges(payload)
    elif step is PipelineStep.DETECT_FILLER:
        state.filler_cut_ranges = _json_to_ranges(payload)
    elif step is PipelineStep.BUILD_EDL:
        state.edl = _json_to_edl(payload, video_id)
    elif step is PipelineStep.RENDER:
        state.rendered_path = Path(json.loads(payload)["output_path"])


def _compute(
    step: PipelineStep,
    container: Container,
    video: Video,
    job_id: JobId,
    state: _State,
    configs: dict[PipelineStep, object],
) -> None:
    config = configs[step]
    if step is PipelineStep.EXTRACT_AUDIO:
        state.audio_path = container.audio_extractor.extract(Path(video.source_path), config)
    elif step is PipelineStep.TRANSCRIBE:
        segment_index = count()
        state.transcript = container.transcriber.transcribe(
            state.audio_path,
            video.id,
            config,
            on_progress=lambda f: container.progress_reporter.report(job_id, step, f),
            on_segment=lambda seg: container.transcript_segment_sink.append(job_id, next(segment_index), seg),
        )
    elif step is PipelineStep.DETECT_SILENCE:
        candidate_gaps = container.silence_detector.detect_candidate_gaps(state.audio_path, config)
        state.silence_cut_ranges = filter_cuttable_silences(candidate_gaps, config)
    elif step is PipelineStep.DETECT_FILLER:
        filler_words = find_filler_words(list(state.transcript.all_words()), config)
        state.filler_cut_ranges = filler_words_to_ranges(filler_words)
    elif step is PipelineStep.BUILD_EDL:
        state.edl = build_edl(
            video.id, video.duration_seconds, state.silence_cut_ranges, state.filler_cut_ranges, config
        )
    elif step is PipelineStep.RENDER:
        output_path = render_output_path(container.settings.resolved_renders_dir(), video.id, job_id)
        state.rendered_path = container.video_renderer.render(Path(video.source_path), state.edl, config, output_path)
    else:
        raise ValueError(f"unsupported step: {step}")


def _findings_for(step: PipelineStep, state: _State) -> dict[str, float] | None:
    if step is PipelineStep.DETECT_SILENCE:
        ranges = state.silence_cut_ranges
    elif step is PipelineStep.DETECT_FILLER:
        ranges = state.filler_cut_ranges
    else:
        return None
    return {"cuts": len(ranges), "seconds_removed": sum(r.duration for r in ranges)}


def render_output_path(renders_dir: Path, video_id: VideoId, job_id: JobId) -> Path:
    """Deterministic rendered-output location, shared with the API's result
    endpoint so it never needs to recompute the RENDER step's config hash to
    find the file."""
    return renders_dir / video_id.value / f"{job_id.value}.mp4"


def compute_step_hashes(job: Job, configs: dict[PipelineStep, object] | None = None) -> dict[PipelineStep, str]:
    """Replays the same config-hash chain _run() computes while executing the
    job, without re-running any steps. Lets read-only endpoints (e.g. fetching
    the cached transcript) rebuild an ArtifactKey for an already-completed job."""
    configs = configs if configs is not None else _step_configs_for(job)
    hashes: dict[PipelineStep, str] = {}
    for step_state in job.steps:
        step = step_state.step
        if step not in configs:
            continue
        own_config = configs[step]
        upstream_hashes = {
            dep: hashes.get(dep, _SKIPPED_STEP_HASH) for dep in STEP_DEPENDENCIES[step]
        }
        hashes[step] = compute_config_hash(step, own_config, upstream_hashes)
    return hashes


def get_transcript(container: Container, video_id: VideoId, job: Job) -> Transcript | None:
    """Fetches the cached TRANSCRIBE artifact for a job, or None if the job
    never requested the step, it hasn't finished yet, or the artifact is
    missing."""
    try:
        step_state = job.step_state(PipelineStep.TRANSCRIBE)
    except StopIteration:
        return None
    if step_state.status not in (StepStatus.DONE, StepStatus.SKIPPED_CACHED):
        return None
    hashes = compute_step_hashes(job)
    key = ArtifactKey(video_id, PipelineStep.TRANSCRIBE, hashes[PipelineStep.TRANSCRIBE])
    payload = container.artifact_repository.get(key)
    if payload is None:
        return None
    return _json_to_transcript(payload, video_id)


def get_edl(container: Container, video_id: VideoId, job: Job) -> EDL | None:
    """Fetches the cached BUILD_EDL artifact for a job, or None if it hasn't
    finished yet or the artifact is missing. Mirrors get_transcript() above."""
    try:
        step_state = job.step_state(PipelineStep.BUILD_EDL)
    except StopIteration:
        return None
    if step_state.status not in (StepStatus.DONE, StepStatus.SKIPPED_CACHED):
        return None
    hashes = compute_step_hashes(job)
    key = ArtifactKey(video_id, PipelineStep.BUILD_EDL, hashes[PipelineStep.BUILD_EDL])
    payload = container.artifact_repository.get(key)
    if payload is None:
        return None
    return _json_to_edl(payload, video_id)


def run_pipeline_job(job_id: str) -> None:
    """Top-level, dotted-path-importable entrypoint for the JobRunner. Builds
    its own Container inside the worker process -- must never be handed to
    JobRunner.enqueue as a closure/bound method (see JobRunner's docstring)."""
    _run(build_container(), JobId(job_id))


def _run(container: Container, job_id: JobId) -> None:
    job = container.job_repository.get(job_id)
    if job is None or job.status in _TERMINAL_JOB_STATUSES:
        return
    video = container.video_repository.get(job.video_id)
    if video is None:
        return

    state = _State()
    configs = _step_configs_for(job)
    hashes = compute_step_hashes(job, configs)
    failed_steps: set[PipelineStep] = set()

    for step_state in job.steps:
        step = step_state.step
        if step not in configs:
            continue  # CHAPTERS/SUBTITLES etc. -- out of scope for v1

        blocking_deps = STEP_DEPENDENCIES[step] & failed_steps
        if blocking_deps:
            failed_dep = next(iter(blocking_deps))
            try:
                job = job.with_step_updated(
                    step, status=StepStatus.FAILED, error=f"upstream step {failed_dep.value} failed"
                )
                container.job_repository.update(job)
            except InvalidJobTransitionError:
                return
            failed_steps.add(step)
            continue

        key = ArtifactKey(video.id, step, hashes[step])

        try:
            cached = container.artifact_repository.get(key)
            if cached is not None:
                _apply_cached(step, cached, video.id, state)
                now = datetime.now(timezone.utc)
                job = job.with_step_updated(
                    step,
                    status=StepStatus.SKIPPED_CACHED,
                    started_at=now,
                    finished_at=now,
                    findings=_findings_for(step, state),
                )
                container.job_repository.update(job)
                continue

            job = job.with_step_updated(step, status=StepStatus.RUNNING, started_at=datetime.now(timezone.utc))
            container.job_repository.update(job)

            _compute(step, container, video, job_id, state, configs)

            container.artifact_repository.put(key, _serialize(step, state))
            job = job.with_step_updated(
                step,
                status=StepStatus.DONE,
                finished_at=datetime.now(timezone.utc),
                findings=_findings_for(step, state),
            )
            container.job_repository.update(job)
        except InvalidJobTransitionError:
            return
        except _PORT_ERRORS as exc:
            failure = Failure(reason=str(exc))
            try:
                job = job.with_step_updated(
                    step,
                    status=StepStatus.FAILED,
                    finished_at=datetime.now(timezone.utc),
                    error=failure.reason,
                    retryable=failure.retryable,
                )
                container.job_repository.update(job)
            except InvalidJobTransitionError:
                return
            failed_steps.add(step)
