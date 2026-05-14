"""Utility helpers shared across node modules.

Provides FFmpeg/ffprobe path resolution and common async subprocess
wrappers. All video-related nodes import from here.
"""

import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Common FFmpeg install locations on Windows
_FFMPEG_SEARCH_PATHS: list[str] = [
    r"C:\ProgramData\chocolatey\bin",
    r"C:\ffmpeg\bin",
    r"C:\Program Files\ffmpeg\bin",
]

# Cached paths — resolved once per process
_ffmpeg_path: str | None = None
_ffprobe_path: str | None = None


def find_ffmpeg() -> str:
    """Locate the ffmpeg executable.

    Checks PATH first, then common Windows install locations.

    Returns:
        Absolute path to ffmpeg executable.

    Raises:
        RuntimeError: If ffmpeg cannot be found anywhere.
    """
    global _ffmpeg_path
    if _ffmpeg_path is not None:
        return _ffmpeg_path

    # Check PATH first
    found = shutil.which("ffmpeg")
    if found:
        _ffmpeg_path = found
        return _ffmpeg_path

    # Check common install directories
    for search_dir in _FFMPEG_SEARCH_PATHS:
        candidate = Path(search_dir) / "ffmpeg.exe"
        if candidate.exists():
            _ffmpeg_path = str(candidate)
            return _ffmpeg_path

    raise RuntimeError(
        "ffmpeg not found on PATH or in common install locations.\n"
        "Install via: choco install ffmpeg-full"
    )


def find_ffprobe() -> str:
    """Locate the ffprobe executable.

    Checks PATH first, then common Windows install locations.

    Returns:
        Absolute path to ffprobe executable.

    Raises:
        RuntimeError: If ffprobe cannot be found anywhere.
    """
    global _ffprobe_path
    if _ffprobe_path is not None:
        return _ffprobe_path

    found = shutil.which("ffprobe")
    if found:
        _ffprobe_path = found
        return _ffprobe_path

    for search_dir in _FFMPEG_SEARCH_PATHS:
        candidate = Path(search_dir) / "ffprobe.exe"
        if candidate.exists():
            _ffprobe_path = str(candidate)
            return _ffprobe_path

    raise RuntimeError(
        "ffprobe not found on PATH or in common install locations.\n"
        "Install via: choco install ffmpeg-full"
    )


def to_ffmpeg_path(path: Path | str) -> str:
    """Convert a Windows path to FFmpeg-safe forward-slash format.

    FFmpeg filter chains use backslash as escape character and colon
    as filter separator. Windows paths break both. This function
    converts all backslashes to forward slashes.

    Also escapes colons in drive letters for filter_complex usage
    (e.g. E:/path becomes E\\\\:/path inside filter strings).
    """
    return str(path).replace("\\", "/")


def to_ffmpeg_filter_path(path: Path | str) -> str:
    """Convert path for use inside FFmpeg -filter_complex strings.

    In addition to forward slashes, colons and backslashes inside
    filter_complex arguments need extra escaping.
    """
    p = str(path).replace("\\", "/")
    # Escape the colon after drive letter for filter_complex
    # E:/path → E\\:/path
    if len(p) >= 2 and p[1] == ":":
        p = p[0] + "\\:" + p[2:]
    return p


async def run_ffmpeg(
    args: list[str],
    description: str = "FFmpeg",
) -> str:
    """Run an FFmpeg command and validate the result.

    Args:
        args: Full command-line arguments (including ffmpeg path).
        description: Human-readable description for logging.

    Returns:
        FFmpeg stderr output (informational).

    Raises:
        RuntimeError: If FFmpeg exits with non-zero return code.
    """
    cmd_str = " ".join(args)
    logger.info(f"[{description}] Running: {cmd_str}")

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    stderr_text = stderr.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        # Show last 500 chars of stderr for debugging
        error_tail = stderr_text[-500:] if len(stderr_text) > 500 else stderr_text
        raise RuntimeError(
            f"[{description}] FFmpeg failed (exit code {proc.returncode}).\n"
            f"Command: {cmd_str}\n"
            f"Stderr (last 500 chars):\n{error_tail}"
        )

    logger.debug(f"[{description}] FFmpeg completed successfully.")
    return stderr_text


async def probe_media(file_path: Path | str) -> dict[str, Any]:
    """Run ffprobe on a media file and return parsed JSON output.

    Args:
        file_path: Path to the media file.

    Returns:
        Parsed JSON dict with format and stream information.

    Raises:
        RuntimeError: If ffprobe fails or output cannot be parsed.
    """
    ffprobe = find_ffprobe()
    args = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration,size",
        "-show_entries", "stream=codec_type,codec_name,duration",
        "-of", "json",
        str(file_path),
    ]

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        stderr_text = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"ffprobe failed on {file_path}: {stderr_text}"
        )

    try:
        return json.loads(stdout.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"ffprobe returned invalid JSON for {file_path}: {e}"
        )
