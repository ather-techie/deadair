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
    log_level: str = "INFO"
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
        return self.sqlite_db_path or (self.data_dir / "deadair.db")


def load_settings() -> Settings:
    """Raises pydantic.ValidationError if DEADAIR_FFMPEG_BINARY_PATH (etc.) is missing."""
    return Settings()
