from dataclasses import dataclass

from redis import Redis

from deadair.application.ports.artifact_repository import ArtifactRepository
from deadair.application.ports.audio_extractor import AudioExtractor
from deadair.application.ports.job_repository import JobRepository
from deadair.application.ports.job_runner import JobRunner
from deadair.application.ports.progress_reporter import ProgressReporter
from deadair.application.ports.silence_detector import SilenceDetector
from deadair.application.ports.transcriber import Transcriber
from deadair.application.ports.video_renderer import VideoRenderer
from deadair.application.ports.video_repository import VideoRepository
from deadair.config import Settings, load_settings
from deadair.infrastructure.jobs.rq_job_runner import RQJobRunner
from deadair.infrastructure.media.faster_whisper_transcriber import FasterWhisperTranscriber
from deadair.infrastructure.media.ffmpeg_audio_extractor import FfmpegAudioExtractor
from deadair.infrastructure.media.ffmpeg_silence_detector import FfmpegSilenceDetector
from deadair.infrastructure.media.ffmpeg_video_renderer import FfmpegVideoRenderer
from deadair.infrastructure.persistence.local_disk.artifact_repository_disk import DiskArtifactRepository
from deadair.infrastructure.persistence.sqlite.connection import create_connection
from deadair.infrastructure.persistence.sqlite.job_repository_sqlite import SqliteJobRepository
from deadair.infrastructure.persistence.sqlite.progress_reporter_sqlite import SqliteProgressReporter
from deadair.infrastructure.persistence.sqlite.video_repository_sqlite import SqliteVideoRepository


@dataclass
class Container:
    settings: Settings
    job_repository: JobRepository
    job_runner: JobRunner
    video_repository: VideoRepository
    artifact_repository: ArtifactRepository
    progress_reporter: ProgressReporter
    audio_extractor: AudioExtractor
    transcriber: Transcriber
    silence_detector: SilenceDetector
    video_renderer: VideoRenderer
    # As of M6, every port has a real adapter: audio_extractor/silence_detector
    # (M4), transcriber (M5), video_renderer/job_runner/progress_reporter (M6).
    # The remaining infrastructure/media/fake_*.py adapters are kept for fast,
    # isolated orchestrator/API tests -- build_container() no longer wires them.


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or load_settings()
    conn = create_connection(settings.resolved_sqlite_db_path())
    redis_connection = Redis.from_url(settings.redis_url)
    return Container(
        settings=settings,
        job_repository=SqliteJobRepository(conn),
        job_runner=RQJobRunner(redis_connection, settings.rq_queue_name),
        video_repository=SqliteVideoRepository(conn),
        artifact_repository=DiskArtifactRepository(settings.data_dir / "artifacts"),
        progress_reporter=SqliteProgressReporter(conn),
        audio_extractor=FfmpegAudioExtractor(settings.ffmpeg_binary_path, settings.data_dir / "audio"),
        transcriber=FasterWhisperTranscriber(settings.whisper_device, settings.whisper_compute_type),
        silence_detector=FfmpegSilenceDetector(settings.ffmpeg_binary_path),
        video_renderer=FfmpegVideoRenderer(settings.ffmpeg_binary_path, settings.data_dir / "render_work"),
    )
