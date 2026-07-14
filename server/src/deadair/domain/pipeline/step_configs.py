from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractAudioConfig:
    sample_rate: int = 16000
    channels: int = 1


@dataclass(frozen=True, slots=True)
class TranscribeConfig:
    model_name: str = "base"
    language: str | None = None


@dataclass(frozen=True, slots=True)
class RenderConfig:
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    crf: int = 18


@dataclass(frozen=True, slots=True)
class ChaptersConfig:
    min_chapter_gap_seconds: float = 30.0


@dataclass(frozen=True, slots=True)
class SubtitlesConfig:
    max_line_chars: int = 42
    format: str = "srt"
