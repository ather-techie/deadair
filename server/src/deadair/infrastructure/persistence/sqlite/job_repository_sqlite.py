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
    filler_words = json.loads(row["filler_words_json"]) if row["filler_words_json"] is not None else None
    filler_case_sensitive = row["filler_case_sensitive"]
    return Job(
        id=JobId(row["id"]),
        video_id=VideoId(row["video_id"]),
        status=JobStatus(row["status"]),
        steps=_json_to_steps(row["steps_json"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        speed_multiplier=row["speed_multiplier"],
        noise_floor_db=row["noise_floor_db"],
        min_silence_duration=row["min_silence_duration"],
        padding_seconds=row["padding_seconds"],
        min_keep_duration=row["min_keep_duration"],
        filler_words=frozenset(filler_words) if filler_words is not None else None,
        filler_case_sensitive=bool(filler_case_sensitive) if filler_case_sensitive is not None else None,
    )


class SqliteJobRepository(JobRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, job: Job) -> None:
        try:
            self._conn.execute(
                "INSERT INTO jobs (id, video_id, status, created_at, updated_at, steps_json, "
                "speed_multiplier, noise_floor_db, min_silence_duration, padding_seconds, "
                "min_keep_duration, filler_words_json, filler_case_sensitive) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    job.id.value,
                    job.video_id.value,
                    job.status.value,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    _steps_to_json(job.steps),
                    job.speed_multiplier,
                    job.noise_floor_db,
                    job.min_silence_duration,
                    job.padding_seconds,
                    job.min_keep_duration,
                    json.dumps(sorted(job.filler_words)) if job.filler_words is not None else None,
                    job.filler_case_sensitive,
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
