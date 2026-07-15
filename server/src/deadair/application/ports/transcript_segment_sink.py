from abc import ABC, abstractmethod

from deadair.domain.entities.transcript import Segment
from deadair.domain.value_objects.ids import JobId


class TranscriptSegmentSink(ABC):
    """Incremental sink for transcript segments as they're produced mid-
    transcription, distinct from ArtifactRepository which only persists the
    complete Transcript once the whole TRANSCRIBE step finishes. Lets the API
    stream segments to the client before the step -- or the job -- is done."""

    @abstractmethod
    def append(self, job_id: JobId, index: int, segment: Segment) -> None: ...

    @abstractmethod
    def list_after(self, job_id: JobId, after_index: int) -> list[tuple[int, Segment]]:
        """Returns (index, segment) pairs with index > after_index, ordered by
        index ascending."""
