from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEADAIR_", env_file=".env", extra="forbid")

    ffmpeg_binary_path: Path = Field(
        ...,
        description="Absolute path to the ffmpeg executable.",
    )
    data_dir: Path = Field(default=Path("./data"))
    sqlite_db_path: Path | None = None
    uploads_dir: Path | None = None
    audio_dir: Path | None = None
    artifacts_dir: Path | None = None
    render_work_dir: Path | None = None
    renders_dir: Path | None = None
    log_level: str = "INFO"
    log_dir: Path = Field(default=Path("./log"))
    # Deployment-level whisper hardware config -- per-job model choice comes
    # from TranscribeConfig.model_name instead (see step_configs.py).
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    redis_url: str = "redis://localhost:6379/0"
    rq_queue_name: str = "deadair"

    @field_validator("ffmpeg_binary_path")
    @classmethod
    def _non_empty(cls, v: Path) -> Path:
        if not str(v).strip():
            raise ValueError("ffmpeg_binary_path must not be empty")
        return v

    def resolved_sqlite_db_path(self) -> Path:
        return (self.sqlite_db_path or (self.data_dir / "deadair.db")).resolve()

    def resolved_uploads_dir(self) -> Path:
        return (self.uploads_dir or (self.data_dir / "uploads")).resolve()

    def resolved_audio_dir(self) -> Path:
        return (self.audio_dir or (self.data_dir / "audio")).resolve()

    def resolved_artifacts_dir(self) -> Path:
        return (self.artifacts_dir or (self.data_dir / "artifacts")).resolve()

    def resolved_render_work_dir(self) -> Path:
        return (self.render_work_dir or (self.data_dir / "render_work")).resolve()

    def resolved_renders_dir(self) -> Path:
        return (self.renders_dir or (self.data_dir / "renders")).resolve()

    def resolved_log_dir(self) -> Path:
        return self.log_dir.resolve()


def load_settings() -> Settings:
    """Raises pydantic.ValidationError if DEADAIR_FFMPEG_BINARY_PATH (etc.) is missing."""
    return Settings()
