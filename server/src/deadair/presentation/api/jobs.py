from fastapi import APIRouter, Depends, HTTPException

from deadair.container import Container
from deadair.domain.entities.job import InvalidJobTransitionError
from deadair.domain.value_objects.ids import JobId
from deadair.presentation.api.deps import get_container
from deadair.presentation.dto.job_dto import JobDTO
from deadair.presentation.mappers.job_mapper import job_to_dto

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str, container: Container = Depends(get_container)) -> JobDTO:
    job = container.job_repository.get(JobId(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job_to_dto(job, container.progress_reporter)


@router.post("/{job_id}/cancel", status_code=204)
def cancel_job(job_id: str, container: Container = Depends(get_container)) -> None:
    job = container.job_repository.get(JobId(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    try:
        cancelled = job.cancel()
    except InvalidJobTransitionError as exc:
        raise HTTPException(status_code=409, detail=f"job already terminal ({job.status.value})") from exc
    container.job_repository.update(cancelled)
