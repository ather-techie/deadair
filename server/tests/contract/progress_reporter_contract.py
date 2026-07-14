import pytest

from deadair.application.ports.progress_reporter import ProgressReporter
from deadair.domain.pipeline.step import PipelineStep
from deadair.domain.value_objects.ids import JobId


class ProgressReporterContractTests:
    """Shared behavioral contract for any ProgressReporter adapter. Subclass
    and provide a `reporter` fixture returning a fresh adapter instance."""

    @pytest.fixture
    def reporter(self) -> ProgressReporter:
        raise NotImplementedError

    def test_get_before_any_report_returns_none(self, reporter):
        assert reporter.get(JobId.new(), PipelineStep.TRANSCRIBE) is None

    def test_report_then_get_returns_fraction_and_message(self, reporter):
        job_id = JobId.new()
        reporter.report(job_id, PipelineStep.TRANSCRIBE, 0.5, "halfway")
        assert reporter.get(job_id, PipelineStep.TRANSCRIBE) == (0.5, "halfway")

    def test_report_overwrites_previous_value(self, reporter):
        job_id = JobId.new()
        reporter.report(job_id, PipelineStep.TRANSCRIBE, 0.5, "halfway")
        reporter.report(job_id, PipelineStep.TRANSCRIBE, 0.9, "almost done")
        assert reporter.get(job_id, PipelineStep.TRANSCRIBE) == (0.9, "almost done")

    def test_progress_is_scoped_per_job_and_step(self, reporter):
        job_a, job_b = JobId.new(), JobId.new()
        reporter.report(job_a, PipelineStep.TRANSCRIBE, 0.2, "a")
        reporter.report(job_a, PipelineStep.EXTRACT_AUDIO, 0.7, "b")
        reporter.report(job_b, PipelineStep.TRANSCRIBE, 0.4, "c")

        assert reporter.get(job_a, PipelineStep.TRANSCRIBE) == (0.2, "a")
        assert reporter.get(job_a, PipelineStep.EXTRACT_AUDIO) == (0.7, "b")
        assert reporter.get(job_b, PipelineStep.TRANSCRIBE) == (0.4, "c")
