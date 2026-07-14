import pytest

from deadair.infrastructure.persistence.sqlite.connection import create_connection
from deadair.infrastructure.persistence.sqlite.job_repository_sqlite import SqliteJobRepository
from tests.contract.job_repository_contract import JobRepositoryContractTests


class TestSqliteJobRepository(JobRepositoryContractTests):
    @pytest.fixture
    def repo(self, tmp_path):
        return SqliteJobRepository(create_connection(tmp_path / "test.db"))
