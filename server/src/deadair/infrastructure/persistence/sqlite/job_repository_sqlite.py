import json
import sqlite3
from datetime import datetime

from deadair.application.ports.job_repository import (
    JobAlreadyExistsError,
    JobNotFoundError,
    JobRepository,
)
from deadair.domain.entities.job import Job, JobStatus, StepState, StepStatus
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import JobId, VideoId


def _steps_to_json(steps: tuple[StepState, ...]) -> str:
    return json.dumps(
        [
            {
                "step": s.step.value,
                "status": s.status.value,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
                "error": s.error,
                "retryable": s.retryable,
                "findings": s.findings,
            }
            for s in steps
        ]
    )


def _json_to_steps(raw: str) -> tuple[StepState, ...]:
    items = json.loads(raw)
    return tuple(
        StepState(
            step=PipelineStep(item["step"]),
            status=StepStatus(item["status"]),
            started_at=datetime.fromisoformat(item["started_at"]) if item["started_at"] else None,
            finished_at=datetime.fromisoformat(item["finished_at"]) if item["finished_at"] else None,
            error=item["error"],
            retryable=item["retryable"],
            findings=item.get("findings"),
        )
        for item in items
    )


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=JobId(row["id"]),
        video_id=VideoId(row["video_id"]),
        status=JobStatus(row["status"]),
        steps=_json_to_steps(row["steps_json"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


class SqliteJobRepository(JobRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, job: Job) -> None:
        try:
            self._conn.execute(
                "INSERT INTO jobs (id, video_id, status, created_at, updated_at, steps_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    job.id.value,
                    job.video_id.value,
                    job.status.value,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    _steps_to_json(job.steps),
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            raise JobAlreadyExistsError(job.id) from exc

    def get(self, job_id: JobId) -> Job | None:
        row = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id.value,)).fetchone()
        return _row_to_job(row) if row else None

    def update(self, job: Job) -> None:
        cur = self._conn.execute(
            "UPDATE jobs SET status=?, updated_at=?, steps_json=? WHERE id=?",
            (job.status.value, job.updated_at.isoformat(), _steps_to_json(job.steps), job.id.value),
        )
        self._conn.commit()
        if cur.rowcount == 0:
            raise JobNotFoundError(job.id)

    def list_for_video(self, video_id: VideoId) -> list[Job]:
        rows = self._conn.execute(
            "SELECT * FROM jobs WHERE video_id = ? ORDER BY created_at", (video_id.value,)
        ).fetchall()
        return [_row_to_job(r) for r in rows]

    def list_active(self) -> list[Job]:
        rows = self._conn.execute(
            "SELECT * FROM jobs WHERE status IN (?, ?) ORDER BY created_at",
            (JobStatus.PENDING.value, JobStatus.RUNNING.value),
        ).fetchall()
        return [_row_to_job(r) for r in rows]
