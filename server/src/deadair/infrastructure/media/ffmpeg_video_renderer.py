import shutil
import uuid
from pathlib import Path

from deadair.application.ports.video_renderer import RenderError, VideoRenderer
from deadair.domain.entities.edl import EDL
from deadair.domain.pipeline.step_configs import RenderConfig
from deadair.infrastructure.media.ffmpeg_runner import FfmpegInvocationError, run_ffmpeg


def _atempo_chain(rate: float) -> str:
    """ffmpeg's atempo filter only accepts a factor in [0.5, 2.0] per
    instance; chain multiple atempo filters (multiplying to `rate`) for
    larger multipliers, e.g. 4.0 -> atempo=2.0,atempo=2.0."""
    factors = []
    remaining = rate
    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0
    factors.append(remaining)
    return ",".join(f"atempo={f}" for f in factors)


class FfmpegVideoRenderer(VideoRenderer):
    """Cuts source_path down to edl.segments by re-encoding each segment
    (input-side -ss/-to seeking, which is frame-accurate even under
    re-encode), then concatenating the segments via ffmpeg's concat demuxer.
    Re-encoding each segment first (rather than -c copy segment cuts) avoids
    keyframe-boundary snapping, which would otherwise clip audio/video near
    each cut's edges. Segments with rate != 1.0 (sped up instead of cut) get
    setpts/atempo filters applied during that same re-encode."""

    _MIN_SEGMENT_TIMEOUT_SECONDS = 300.0
    _SEGMENT_TIMEOUT_MULTIPLIER = 10.0

    def __init__(self, ffmpeg_binary_path: Path, work_dir: Path):
        self._ffmpeg_binary_path = Path(ffmpeg_binary_path)
        self._work_dir = Path(work_dir)

    def render(self, source_path: Path, edl: EDL, config: RenderConfig, output_path: Path) -> Path:
        if not edl.segments:
            raise RenderError("EDL has no segments -- nothing to render")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        job_dir = self._work_dir / uuid.uuid4().hex
        job_dir.mkdir(parents=True, exist_ok=True)
        try:
            segments = self._cut_segments(Path(source_path), edl, config, job_dir)
            if len(segments) == 1:
                shutil.copy(segments[0], output_path)
            else:
                self._concat_segments(segments, output_path)
        except FfmpegInvocationError as exc:
            raise RenderError(str(exc)) from exc
        finally:
            shutil.rmtree(job_dir, ignore_errors=True)
        return output_path

    def _cut_segments(self, source_path: Path, edl: EDL, config: RenderConfig, job_dir: Path) -> list[Path]:
        segments = []
        for i, seg in enumerate(edl.segments):
            segment_path = job_dir / f"segment_{i:04d}.mp4"
            timeout = max(
                self._MIN_SEGMENT_TIMEOUT_SECONDS,
                seg.range.duration * self._SEGMENT_TIMEOUT_MULTIPLIER,
            )
            args = ["-y", "-ss", str(seg.range.start), "-to", str(seg.range.end), "-i", str(source_path)]
            if seg.rate != 1.0:
                args += ["-filter:v", f"setpts=PTS/{seg.rate}", "-filter:a", _atempo_chain(seg.rate)]
            args += [
                "-c:v",
                config.video_codec,
                "-c:a",
                config.audio_codec,
                "-crf",
                str(config.crf),
                str(segment_path),
            ]
            run_ffmpeg(self._ffmpeg_binary_path, args, timeout=timeout)
            segments.append(segment_path)
        return segments

    def _concat_segments(self, segments: list[Path], output_path: Path) -> None:
        list_path = segments[0].parent / "concat_list.txt"
        list_path.write_text("".join(f"file '{p.name}'\n" for p in segments))
        run_ffmpeg(
            self._ffmpeg_binary_path,
            ["-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(output_path)],
        )
