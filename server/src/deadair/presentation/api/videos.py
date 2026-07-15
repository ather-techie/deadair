import hashlib

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from deadair.application.use_cases.run_pipeline_job import get_transcript, render_output_path, run_pipeline_job
from deadair.container import Container
from deadair.domain.entities.job import Job, StepStatus
from deadair.domain.entities.video import Video
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import VideoId
from deadair.infrastructure.media.video_prober import probe_video
from deadair.presentation.api.deps import get_container
from deadair.presentation.dto.transcript_dto import PartialTranscriptDTO, TranscriptDTO
from deadair.presentation.dto.video_dto import UploadResponseDTO, VideoDTO
from deadair.presentation.mappers.transcript_mapper import partial_transcript_to_dto, transcript_to_dto
from deadair.presentation.mappers.video_mapper import video_to_dto

router = APIRouter(prefix="/api/videos", tags=["videos"])


def _selected_steps(
    *, remove_silence: bool, remove_filler: bool, show_transcript: bool = False
) -> tuple[PipelineStep, ...]:
    """MVP step subset for a job, built in PipelineStep declaration order (the
    topological order STEP_DEPENDENCIES relies on). EXTRACT_AUDIO/BUILD_EDL/RENDER
    are structural and always included; DETECT_SILENCE is only included if
    remove_silence is on; TRANSCRIBE runs if either remove_filler or
    show_transcript is on (both need a transcript, one to cut filler words, the
    other just to display it); DETECT_FILLER is only included if remove_filler
    is on."""
    steps = [PipelineStep.EXTRACT_AUDIO]
    if remove_filler or show_transcript:
        steps.append(PipelineStep.TRANSCRIBE)
    if remove_silence:
        steps.append(PipelineStep.DETECT_SILENCE)
    if remove_filler:
        steps.append(PipelineStep.DETECT_FILLER)
    steps += [PipelineStep.BUILD_EDL, PipelineStep.RENDER]
    return tuple(steps)


@router.post("", status_code=201)
async def upload_video(
    video: UploadFile = File(...),
    remove_silence: bool = Form(...),
    remove_filler: bool = Form(...),
    show_transcript: bool = Form(False),
    container: Container = Depends(get_container),
) -> UploadResponseDTO:
    if not remove_silence and not remove_filler and not show_transcript:
        raise HTTPException(
            status_code=400, detail="select at least one of remove_silence, remove_filler, show_transcript"
        )

    video_id = VideoId.new()
    upload_dir = container.settings.resolved_uploads_dir() / video_id.value
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest_path = upload_dir / (video.filename or "upload")

    hasher = hashlib.sha256()
    with dest_path.open("wb") as f:
        while chunk := await video.read(1024 * 1024):
            hasher.update(chunk)
            f.write(chunk)

    duration, fps, width, height = probe_video(container.settings.ffmpeg_binary_path, dest_path)

    domain_video = Video(
        id=video_id,
        source_path=str(dest_path),
        content_hash=hasher.hexdigest(),
        duration_seconds=duration,
        fps=fps,
        width=width,
        height=height,
    )
    container.video_repository.add(domain_video)

    job = Job.create(
        video_id,
        steps=_selected_steps(
            remove_silence=remove_silence, remove_filler=remove_filler, show_transcript=show_transcript
        ),
    )
    container.job_repository.add(job)
    container.job_runner.enqueue(run_pipeline_job, str(job.id))

    return UploadResponseDTO(video_id=video_id.value, job_id=job.id.value)


@router.get("")
def list_videos(container: Container = Depends(get_container)) -> list[VideoDTO]:
    return [video_to_dto(v) for v in container.video_repository.list_all()]


@router.get("/{video_id}")
def get_video(video_id: str, container: Container = Depends(get_container)) -> VideoDTO:
    domain_video = container.video_repository.get(VideoId(video_id))
    if domain_video is None:
        raise HTTPException(status_code=404, detail="video not found")
    return video_to_dto(domain_video)


@router.get("/{video_id}/result")
def get_result(video_id: str, container: Container = Depends(get_container)) -> FileResponse:
    vid = VideoId(video_id)
    if container.video_repository.get(vid) is None:
        raise HTTPException(status_code=404, detail="video not found")

    jobs = container.job_repository.list_for_video(vid)
    if not jobs:
        raise HTTPException(status_code=404, detail="no job for this video")
    latest_job = jobs[-1]

    render_step = latest_job.step_state(PipelineStep.RENDER)
    if render_step.status != StepStatus.DONE:
        raise HTTPException(status_code=409, detail=f"render not ready (status={render_step.status.value})")

    output_path = render_output_path(container.settings.resolved_renders_dir(), vid, latest_job.id)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="rendered file missing on disk")
    return FileResponse(output_path)


@router.get("/{video_id}/transcript")
def get_video_transcript(video_id: str, container: Container = Depends(get_container)) -> TranscriptDTO:
    vid = VideoId(video_id)
    if container.video_repository.get(vid) is None:
        raise HTTPException(status_code=404, detail="video not found")

    jobs = container.job_repository.list_for_video(vid)
    if not jobs:
        raise HTTPException(status_code=404, detail="no job for this video")
    latest_job = jobs[-1]

    transcript = get_transcript(container, vid, latest_job)
    if transcript is None:
        raise HTTPException(status_code=409, detail="transcript not requested or not ready yet")
    return transcript_to_dto(transcript)


@router.get("/{video_id}/transcript/partial")
def get_video_transcript_partial(
    video_id: str, after: int = -1, container: Container = Depends(get_container)
) -> PartialTranscriptDTO:
    vid = VideoId(video_id)
    if container.video_repository.get(vid) is None:
        raise HTTPException(status_code=404, detail="video not found")

    jobs = container.job_repository.list_for_video(vid)
    if not jobs:
        raise HTTPException(status_code=404, detail="no job for this video")
    latest_job = jobs[-1]

    try:
        step_state = latest_job.step_state(PipelineStep.TRANSCRIBE)
    except StopIteration:
        raise HTTPException(status_code=409, detail="transcript not requested for this job") from None

    indexed_segments = container.transcript_segment_sink.list_after(latest_job.id, after)
    finished = step_state.status in (StepStatus.DONE, StepStatus.SKIPPED_CACHED, StepStatus.FAILED)
    return partial_transcript_to_dto(indexed_segments, after, finished)
