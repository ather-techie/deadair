import pytest

from deadair.application.ports.transcript_segment_sink import TranscriptSegmentSink
from deadair.domain.entities.transcript import Segment, Word
from deadair.domain.value_objects.ids import JobId


def _segment(text: str, start: float = 0.0, end: float = 1.0) -> Segment:
    words = (Word(text=text, start=start, end=end, confidence=0.9),)
    return Segment(words=words, start=start, end=end, text=text)


class TranscriptSegmentSinkContractTests:
    """Shared behavioral contract for any TranscriptSegmentSink adapter.
    Subclass and provide a `sink` fixture returning a fresh adapter instance."""

    @pytest.fixture
    def sink(self) -> TranscriptSegmentSink:
        raise NotImplementedError

    def test_list_after_with_no_segments_returns_empty(self, sink):
        assert sink.list_after(JobId.new(), after_index=-1) == []

    def test_appended_segments_are_returned_in_index_order(self, sink):
        job_id = JobId.new()
        sink.append(job_id, 0, _segment("hello"))
        sink.append(job_id, 1, _segment("world"))

        results = sink.list_after(job_id, after_index=-1)

        assert [i for i, _ in results] == [0, 1]
        assert [s.text for _, s in results] == ["hello", "world"]

    def test_list_after_only_returns_segments_past_the_cursor(self, sink):
        job_id = JobId.new()
        sink.append(job_id, 0, _segment("hello"))
        sink.append(job_id, 1, _segment("world"))

        results = sink.list_after(job_id, after_index=0)

        assert [i for i, _ in results] == [1]

    def test_segments_are_scoped_per_job(self, sink):
        job_a, job_b = JobId.new(), JobId.new()
        sink.append(job_a, 0, _segment("a"))
        sink.append(job_b, 0, _segment("b"))

        assert [s.text for _, s in sink.list_after(job_a, after_index=-1)] == ["a"]
        assert [s.text for _, s in sink.list_after(job_b, after_index=-1)] == ["b"]

    def test_segment_words_round_trip(self, sink):
        job_id = JobId.new()
        segment = Segment(
            words=(Word(text="um", start=0.0, end=0.4, confidence=0.9),),
            start=0.0,
            end=0.4,
            text="um",
        )
        sink.append(job_id, 0, segment)

        [(_, roundtripped)] = sink.list_after(job_id, after_index=-1)
        assert roundtripped.words == segment.words
