import json
import subprocess
from pathlib import Path


def probe_video(
    ffmpeg_binary_path: Path, video_path: Path
) -> tuple[float, float | None, int | None, int | None]:
    """Returns (duration_seconds, fps, width, height) via ffprobe (assumed to
    live alongside the configured ffmpeg binary). Falls back to
    (0.0, None, None, None) if ffprobe is unavailable or the probe fails --
    upload should never hard-fail just because metadata couldn't be read."""
    try:
        result = subprocess.run(
            [
                str(_ffprobe_path(ffmpeg_binary_path)),
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "format=duration:stream=width,height,r_frame_rate",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        data = json.loads(result.stdout)
        duration = float(data.get("format", {}).get("duration", 0.0))
        streams = data.get("streams") or [{}]
        stream = streams[0]
        return duration, _parse_frame_rate(stream.get("r_frame_rate")), stream.get("width"), stream.get("height")
    except Exception:
        return 0.0, None, None, None


def _ffprobe_path(ffmpeg_binary_path: Path) -> Path:
    name = "ffprobe.exe" if ffmpeg_binary_path.suffix.lower() == ".exe" else "ffprobe"
    return ffmpeg_binary_path.parent / name


def _parse_frame_rate(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        num, _, den = raw.partition("/")
        den_value = float(den) if den else 1.0
        return float(num) / den_value if den_value != 0 else None
    except ValueError:
        return None
