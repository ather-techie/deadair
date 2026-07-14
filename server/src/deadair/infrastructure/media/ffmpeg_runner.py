import subprocess
from pathlib import Path


class FfmpegInvocationError(Exception):
    def __init__(self, args: list[str], returncode: int, stderr: str):
        stderr_tail = "\n".join(stderr.strip().splitlines()[-20:])
        super().__init__(f"ffmpeg exited {returncode}: {' '.join(args)}\n{stderr_tail}")
        self.returncode = returncode
        self.stderr = stderr


def run_ffmpeg(ffmpeg_binary_path: Path, args: list[str], timeout: float = 300.0) -> subprocess.CompletedProcess:
    """Runs `ffmpeg_binary_path` with args, raising FfmpegInvocationError on a
    non-zero exit code. Returns the completed process (stdout/stderr as
    text) on success."""
    full_args = [str(ffmpeg_binary_path), *args]
    result = subprocess.run(full_args, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise FfmpegInvocationError(full_args, result.returncode, result.stderr)
    return result
