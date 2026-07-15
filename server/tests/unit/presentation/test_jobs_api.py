import io

from deadair.domain.entities.job import Job, JobStatus
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import VideoId


def test_get_job_not_found_returns_404(client):
    response = client.get("/api/jobs/does-not-exist")
    assert response.status_code == 404


def test_cancel_pending_job_marks_it_cancelled(client, container):
    job = Job.create(VideoId.new(), steps=tuple(PipelineStep))
    container.job_repository.add(job)

    response = client.post(f"/api/jobs/{job.id.value}/cancel")

    assert response.status_code == 204
    assert container.job_repository.get(job.id).status == JobStatus.CANCELLED


def test_cancel_terminal_job_returns_409(client):
    upload = client.post(
        "/api/videos",
        files={"video": ("clip.mp4", io.BytesIO(b"data"), "video/mp4")},
        data={"remove_silence": "true", "remove_filler": "true"},
    )
    job_id = upload.json()["job_id"]

    response = client.post(f"/api/jobs/{job_id}/cancel")

    assert response.status_code == 409


def test_cancel_unknown_job_returns_404(client):
    response = client.post("/api/jobs/does-not-exist/cancel")
    assert response.status_code == 404
