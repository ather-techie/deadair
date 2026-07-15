from deadair.application.ports.transcript_segment_sink import TranscriptSegmentSink
from deadair.domain.entities.transcript import Segment
from deadair.domain.value_objects.ids import JobId


class InMemoryTranscriptSegmentSink(TranscriptSegmentSink):
    def __init__(self) -> None:
        self._segments: dict[str, list[tuple[int, Segment]]] = {}

    def append(self, job_id: JobId, index: int, segment: Segment) -> None:
        self._segments.setdefault(job_id.value, []).append((index, segment))

    def list_after(self, job_id: JobId, after_index: int) -> list[tuple[int, Segment]]:
        return [pair for pair in self._segments.get(job_id.value, []) if pair[0] > after_index]
