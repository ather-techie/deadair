import pytest

from deadair.infrastructure.persistence.sqlite.connection import create_connection
from deadair.infrastructure.persistence.sqlite.transcript_segment_sink_sqlite import SqliteTranscriptSegmentSink
from tests.contract.transcript_segment_sink_contract import TranscriptSegmentSinkContractTests


class TestSqliteTranscriptSegmentSink(TranscriptSegmentSinkContractTests):
    @pytest.fixture
    def sink(self, tmp_path):
        return SqliteTranscriptSegmentSink(create_connection(tmp_path / "test.db"))
