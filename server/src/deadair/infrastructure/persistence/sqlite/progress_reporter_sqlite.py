import sqlite3
from datetime import datetime, timezone

from deadair.application.ports.progress_reporter import ProgressReporter
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import JobId


class SqliteProgressReporter(ProgressReporter):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def report(self, job_id: JobId, step: PipelineStep, fraction_complete: float, message: str = "") -> None:
        self._conn.execute(
            "INSERT INTO progress (job_id, step, fraction_complete, message, updated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(job_id, step) DO UPDATE SET "
            "fraction_complete=excluded.fraction_complete, message=excluded.message, "
            "updated_at=excluded.updated_at",
            (job_id.value, step.value, fraction_complete, message, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def get(self, job_id: JobId, step: PipelineStep) -> tuple[float, str] | None:
        row = self._conn.execute(
            "SELECT fraction_complete, message FROM progress WHERE job_id = ? AND step = ?",
            (job_id.value, step.value),
        ).fetchone()
        return (row["fraction_complete"], row["message"]) if row else None
