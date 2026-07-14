import wave

import pytest

from deadair.domain.pipeline.step_configs import ExtractAudioConfig
from deadair.infrastructure.media.ffmpeg_audio_extractor import FfmpegAudioExtractor

pytestmark = pytest.mark.slow


def test_extract_produces_wav_with_configured_sample_rate_and_channels(
    tmp_path, ffmpeg_binary_path, fixture_video_path
):
    extractor = FfmpegAudioExtractor(ffmpeg_binary_path, tmp_path)
    config = ExtractAudioConfig(sample_rate=16000, channels=1)

    output_path = extractor.extract(fixture_video_path, config)

    assert output_path.exists()
    with wave.open(str(output_path), "rb") as wav:
        assert wav.getframerate() == 16000
        assert wav.getnchannels() == 1
        assert wav.getnframes() > 0
