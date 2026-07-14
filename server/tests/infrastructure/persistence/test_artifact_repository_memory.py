import pytest

from deadair.infrastructure.persistence.in_memory.artifact_repository_memory import (
    InMemoryArtifactRepository,
)
from tests.contract.artifact_repository_contract import ArtifactRepositoryContractTests


class TestInMemoryArtifactRepository(ArtifactRepositoryContractTests):
    @pytest.fixture
    def repo(self):
        return InMemoryArtifactRepository()
