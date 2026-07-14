import pytest

from deadair.infrastructure.persistence.sqlite.connection import create_connection
from deadair.infrastructure.persistence.sqlite.video_repository_sqlite import SqliteVideoRepository
from tests.contract.video_repository_contract import VideoRepositoryContractTests


class TestSqliteVideoRepository(VideoRepositoryContractTests):
    @pytest.fixture
    def repo(self, tmp_path):
        return SqliteVideoRepository(create_connection(tmp_path / "test.db"))
