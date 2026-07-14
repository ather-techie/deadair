import pytest

from deadair.infrastructure.persistence.in_memory.video_repository_memory import InMemoryVideoRepository
from tests.contract.video_repository_contract import VideoRepositoryContractTests


class TestInMemoryVideoRepository(VideoRepositoryContractTests):
    @pytest.fixture
    def repo(self):
        return InMemoryVideoRepository()
