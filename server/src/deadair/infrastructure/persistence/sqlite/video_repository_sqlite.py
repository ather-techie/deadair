import sqlite3

from deadair.application.ports.video_repository import VideoRepository
from deadair.domain.entities.video import Video
from deadair.domain.value_objects.ids import VideoId


def _row_to_video(row: sqlite3.Row) -> Video:
    return Video(
        id=VideoId(row["id"]),
        source_path=row["source_path"],
        content_hash=row["content_hash"],
        duration_seconds=row["duration_seconds"],
        fps=row["fps"],
        width=row["width"],
        height=row["height"],
    )


class SqliteVideoRepository(VideoRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, video: Video) -> None:
        self._conn.execute(
            "INSERT INTO videos (id, source_path, content_hash, duration_seconds, fps, width, height) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                video.id.value,
                video.source_path,
                video.content_hash,
                video.duration_seconds,
                video.fps,
                video.width,
                video.height,
            ),
        )
        self._conn.commit()

    def get(self, video_id: VideoId) -> Video | None:
        row = self._conn.execute("SELECT * FROM videos WHERE id = ?", (video_id.value,)).fetchone()
        return _row_to_video(row) if row else None

    def list_all(self) -> list[Video]:
        rows = self._conn.execute("SELECT * FROM videos").fetchall()
        return [_row_to_video(r) for r in rows]

    def delete(self, video_id: VideoId) -> None:
        self._conn.execute("DELETE FROM videos WHERE id = ?", (video_id.value,))
        self._conn.commit()
