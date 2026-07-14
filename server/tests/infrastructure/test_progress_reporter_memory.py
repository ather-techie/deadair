import pytest

from deadair.infrastructure.progress.in_memory_progress_reporter import InMemoryProgressReporter
from tests.contract.progress_reporter_contract import ProgressReporterContractTests


class TestInMemoryProgressReporter(ProgressReporterContractTests):
    @pytest.fixture
    def reporter(self):
        return InMemoryProgressReporter()
