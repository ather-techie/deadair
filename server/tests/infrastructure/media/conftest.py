import shutil
from pathlib import Path

import pytest

FIXTURE_VIDEO_PATH = Path(__file__).parent.parent.parent / "fixtures" / "tone_silence_tone.mp4"
FIXTURE_SPEECH_PATH = Path(__file__).parent.parent.parent / "fixtures" / "speech_sample.wav"


@pytest.fixture
def ffmpeg_binary_path() -> Path:
    found = shutil.which("ffmpeg")
    if not found:
        pytest.skip("ffmpeg binary not found on PATH")
    return Path(found)


@pytest.fixture
def fixture_video_path() -> Path:
    return FIXTURE_VIDEO_PATH


@pytest.fixture
def fixture_speech_path() -> Path:
    return FIXTURE_SPEECH_PATH


@pytest.fixture
def ffprobe_binary_path(ffmpeg_binary_path: Path) -> Path:
    found = shutil.which("ffprobe")
    if not found:
        pytest.skip("ffprobe binary not found on PATH")
    return Path(found)
