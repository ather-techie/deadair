import pytest

from deadair.infrastructure.progress.in_memory_transcript_segment_sink import InMemoryTranscriptSegmentSink
from tests.contract.transcript_segment_sink_contract import TranscriptSegmentSinkContractTests


class TestInMemoryTranscriptSegmentSink(TranscriptSegmentSinkContractTests):
    @pytest.fixture
    def sink(self):
        return InMemoryTranscriptSegmentSink()
