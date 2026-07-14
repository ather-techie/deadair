import pytest

from deadair.domain.pipeline.step_configs import ExtractAudioConfig
from deadair.domain.policies.silence_policy import SilenceDetectionConfig
from deadair.infrastructure.media.ffmpeg_audio_extractor import FfmpegAudioExtractor
from deadair.infrastructure.media.ffmpeg_silence_detector import FfmpegSilenceDetector

pytestmark = pytest.mark.slow


def test_detects_the_fixtures_known_silent_gap(tmp_path, ffmpeg_binary_path, fixture_video_path):
    audio_path = FfmpegAudioExtractor(ffmpeg_binary_path, tmp_path).extract(
        fixture_video_path, ExtractAudioConfig()
    )
    detector = FfmpegSilenceDetector(ffmpeg_binary_path)

    gaps = detector.detect_candidate_gaps(audio_path, SilenceDetectionConfig())

    assert len(gaps) == 1
    gap = gaps[0]
    # The fixture is 1s tone, 1s silence, 1s tone -- allow slack for encoder
    # startup/flush jitter around the boundaries.
    assert gap.start == pytest.approx(1.0, abs=0.2)
    assert gap.end == pytest.approx(2.0, abs=0.2)


def test_no_gaps_when_min_duration_exceeds_the_silence(tmp_path, ffmpeg_binary_path, fixture_video_path):
    audio_path = FfmpegAudioExtractor(ffmpeg_binary_path, tmp_path).extract(
        fixture_video_path, ExtractAudioConfig()
    )
    detector = FfmpegSilenceDetector(ffmpeg_binary_path)

    gaps = detector.detect_candidate_gaps(
        audio_path, SilenceDetectionConfig(min_silence_duration=5.0)
    )

    assert gaps == []
