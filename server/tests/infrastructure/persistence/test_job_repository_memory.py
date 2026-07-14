import pytest

from deadair.infrastructure.persistence.in_memory.job_repository_memory import InMemoryJobRepository
from tests.contract.job_repository_contract import JobRepositoryContractTests


class TestInMemoryJobRepository(JobRepositoryContractTests):
    @pytest.fixture
    def repo(self):
        return InMemoryJobRepository()
