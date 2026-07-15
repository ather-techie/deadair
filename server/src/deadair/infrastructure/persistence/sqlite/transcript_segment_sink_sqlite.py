import json
import sqlite3

from deadair.application.ports.transcript_segment_sink import TranscriptSegmentSink
from deadair.domain.entities.transcript import Segment, Word
from deadair.domain.value_objects.ids import JobId


class SqliteTranscriptSegmentSink(TranscriptSegmentSink):
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def append(self, job_id: JobId, index: int, segment: Segment) -> None:
        words_json = json.dumps(
            [{"text": w.text, "start": w.start, "end": w.end, "confidence": w.confidence} for w in segment.words]
        )
        self._conn.execute(
            "INSERT OR REPLACE INTO transcript_segments "
            "(job_id, seg_index, start_time, end_time, text, words_json) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id.value, index, segment.start, segment.end, segment.text, words_json),
        )
        self._conn.commit()

    def list_after(self, job_id: JobId, after_index: int) -> list[tuple[int, Segment]]:
        rows = self._conn.execute(
            "SELECT seg_index, start_time, end_time, text, words_json FROM transcript_segments "
            "WHERE job_id = ? AND seg_index > ? ORDER BY seg_index ASC",
            (job_id.value, after_index),
        ).fetchall()
        result = []
        for row in rows:
            words = tuple(Word(**w) for w in json.loads(row["words_json"]))
            segment = Segment(words=words, start=row["start_time"], end=row["end_time"], text=row["text"])
            result.append((row["seg_index"], segment))
        return result
