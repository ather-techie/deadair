import re
from pathlib import Path

from deadair.application.ports.silence_detector import SilenceDetectionError, SilenceDetector
from deadair.domain.policies.silence_policy import SilenceDetectionConfig
from deadair.domain.value_objects.time_range import TimeRange
from deadair.infrastructure.media.ffmpeg_runner import FfmpegInvocationError, run_ffmpeg

_SILENCE_START_RE = re.compile(r"silence_start:\s*(-?\d+(?:\.\d+)?)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*(-?\d+(?:\.\d+)?)")


class FfmpegSilenceDetector(SilenceDetector):
    def __init__(self, ffmpeg_binary_path: Path):
        self._ffmpeg_binary_path = Path(ffmpeg_binary_path)

    def detect_candidate_gaps(self, audio_path: Path, config: SilenceDetectionConfig) -> list[TimeRange]:
        audio_filter = f"silencedetect=noise={config.noise_floor_db}dB:d={config.min_silence_duration}"
        try:
            result = run_ffmpeg(
                self._ffmpeg_binary_path,
                ["-i", str(audio_path), "-af", audio_filter, "-f", "null", "-"],
            )
        except FfmpegInvocationError as exc:
            raise SilenceDetectionError(str(exc)) from exc
        return _parse_silence_gaps(result.stderr)


def _parse_silence_gaps(stderr: str) -> list[TimeRange]:
    starts = [float(m.group(1)) for m in _SILENCE_START_RE.finditer(stderr)]
    ends = [float(m.group(1)) for m in _SILENCE_END_RE.finditer(stderr)]
    return [TimeRange(start, end) for start, end in zip(starts, ends)]
