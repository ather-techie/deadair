import pytest

from deadair.infrastructure.persistence.sqlite.connection import create_connection
from deadair.infrastructure.persistence.sqlite.progress_reporter_sqlite import SqliteProgressReporter
from tests.contract.progress_reporter_contract import ProgressReporterContractTests


class TestSqliteProgressReporter(ProgressReporterContractTests):
    @pytest.fixture
    def reporter(self, tmp_path):
        return SqliteProgressReporter(create_connection(tmp_path / "test.db"))
