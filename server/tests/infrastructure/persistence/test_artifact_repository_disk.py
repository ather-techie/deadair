import pytest

from deadair.infrastructure.persistence.local_disk.artifact_repository_disk import (
    DiskArtifactRepository,
)
from tests.contract.artifact_repository_contract import ArtifactRepositoryContractTests


class TestDiskArtifactRepository(ArtifactRepositoryContractTests):
    @pytest.fixture
    def repo(self, tmp_path):
        return DiskArtifactRepository(tmp_path / "artifacts")
