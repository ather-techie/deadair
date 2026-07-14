import subprocess

import pytest

from deadair.application.ports.video_renderer import RenderError
from deadair.domain.entities.edl import EDL
from deadair.domain.pipeline.step_configs import RenderConfig
from deadair.domain.value_objects.ids import VideoId
from deadair.domain.value_objects.time_range import TimeRange
from deadair.infrastructure.media.ffmpeg_video_renderer import FfmpegVideoRenderer

pytestmark = pytest.mark.slow


def _probe_duration(ffprobe_binary_path, path) -> float:
    result = subprocess.run(
        [
            str(ffprobe_binary_path),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def test_render_cuts_out_the_dropped_range(
    tmp_path, ffmpeg_binary_path, ffprobe_binary_path, fixture_video_path
):
    # Fixture is 1s tone, 1s silence, 1s tone -- keep the two tones, drop the middle.
    edl = EDL(
        video_id=VideoId.new(),
        keep_ranges=(TimeRange(0.0, 1.0), TimeRange(2.0, 3.0)),
        total_duration=3.0,
    )
    renderer = FfmpegVideoRenderer(ffmpeg_binary_path, tmp_path / "work")
    output_path = tmp_path / "rendered.mp4"

    result = renderer.render(fixture_video_path, edl, RenderConfig(), output_path)

    assert result == output_path
    assert output_path.exists()
    duration = _probe_duration(ffprobe_binary_path, output_path)
    assert duration == pytest.approx(2.0, abs=0.3)


def test_render_raises_when_edl_has_no_keep_ranges(tmp_path, ffmpeg_binary_path, fixture_video_path):
    edl = EDL(video_id=VideoId.new(), keep_ranges=(), total_duration=3.0)
    renderer = FfmpegVideoRenderer(ffmpeg_binary_path, tmp_path / "work")

    with pytest.raises(RenderError):
        renderer.render(fixture_video_path, edl, RenderConfig(), tmp_path / "out.mp4")
