import hashlib

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from deadair.application.use_cases.run_pipeline_job import render_output_path, run_pipeline_job
from deadair.container import Container
from deadair.domain.entities.job import Job, StepStatus
from deadair.domain.entities.video import Video
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import VideoId
from deadair.infrastructure.media.video_prober import probe_video
from deadair.presentation.api.deps import get_container
from deadair.presentation.dto.video_dto import UploadResponseDTO, VideoDTO
from deadair.presentation.mappers.video_mapper import video_to_dto

router = APIRouter(prefix="/api/videos", tags=["videos"])

MVP_STEPS = (
    PipelineStep.EXTRACT_AUDIO,
    PipelineStep.TRANSCRIBE,
    PipelineStep.DETECT_SILENCE,
    PipelineStep.DETECT_FILLER,
    PipelineStep.BUILD_EDL,
    PipelineStep.RENDER,
)


@router.post("", status_code=201)
async def upload_video(
    video: UploadFile = File(...), container: Container = Depends(get_container)
) -> UploadResponseDTO:
    video_id = VideoId.new()
    upload_dir = container.settings.data_dir / "uploads" / video_id.value
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

    job = Job.create(video_id, steps=MVP_STEPS)
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

    output_path = render_output_path(container.settings.data_dir, vid, latest_job.id)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="rendered file missing on disk")
    return FileResponse(output_path)
