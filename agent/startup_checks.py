"""Startup health checks for the YT Shorts Agent.

Run these checks BEFORE any pipeline code executes.
Validates external dependencies, credentials, disk space,
and FFmpeg capabilities. Fail loud at startup, not silently
at 2AM mid-pipeline.
"""

import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Root of the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def check_ffmpeg_libass() -> None:
    """Verify FFmpeg is installed and has libass subtitle support.

    Runs `ffmpeg -filters` and checks for the `ass` filter.
    Hard-fails with install instructions if missing.

    Raises:
        RuntimeError: If FFmpeg is not installed or lacks libass.
    """
    from agent.utils import find_ffmpeg

    try:
        ffmpeg_bin = find_ffmpeg()
    except RuntimeError:
        raise RuntimeError(
            "FFmpeg is not installed or not on PATH.\n"
            "Install via: choco install ffmpeg-full\n"
            "Or download from: https://www.gyan.dev/ffmpeg/builds/ "
            "(use the 'full' build, NOT 'essentials')"
        )

    try:
        proc = await asyncio.create_subprocess_exec(
            ffmpeg_bin, "-filters",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg is not installed or not on PATH.\n"
            "Install via: choco install ffmpeg-full\n"
            "Or download from: https://www.gyan.dev/ffmpeg/builds/ "
            "(use the 'full' build, NOT 'essentials')"
        )

    filters_output = stdout.decode("utf-8", errors="replace")

    if "ass" not in filters_output:
        raise RuntimeError(
            "FFmpeg is installed but missing libass support.\n"
            "The 'ass' subtitle filter is required for .ass "
            "subtitle burn-in.\n"
            "Fix: reinstall FFmpeg with libass:\n"
            "  choco install ffmpeg-full\n"
            "  OR download the 'full' build from "
            "https://www.gyan.dev/ffmpeg/builds/"
        )


def check_disk_space(min_gb: float) -> None:
    """Check free disk space on the project drive.

    Logs a warning if below threshold but does NOT raise.
    The pipeline should still attempt to run — it may succeed
    if the video is small enough.

    Args:
        min_gb: Minimum free space in GB to consider healthy.
    """
    drive = PROJECT_ROOT.anchor  # e.g. "E:\\"
    usage = shutil.disk_usage(drive)
    free_gb = usage.free / (1024 ** 3)

    if free_gb < min_gb:
        logger.warning(
            f"Low disk space on {drive}: {free_gb:.1f} GB free "
            f"(threshold: {min_gb} GB). "
            f"Pipeline may fail if output files are large."
        )
    else:
        logger.debug(
            f"Disk space OK: {free_gb:.1f} GB free on {drive}"
        )


def check_env_variables() -> None:
    """Verify all required .env keys are present and non-empty.

    Loads .env file from project root, then checks for required keys.

    Raises:
        RuntimeError: Listing every missing or empty env variable.
    """
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        logger.warning(
            f".env file not found at {env_path}. "
            f"Copy .env.template to .env and fill in values."
        )

    required_keys: list[str] = [
        "GEMINI_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]

    missing: list[str] = []
    for key in required_keys:
        value = os.environ.get(key, "").strip()
        if not value:
            missing.append(key)

    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"Missing required environment variables: {joined}\n"
            f"Set them in your .env file (see .env.template)."
        )


def check_credentials_exist() -> None:
    """Check that OAuth credential files exist.

    google_oauth.json is required — this is the OAuth client config
    downloaded from Google Cloud Console.

    token.json is optional at startup — it's generated after the
    first browser-based OAuth flow via auth_flow.py.

    Does NOT raise on missing token.json — just logs instructions.

    Raises:
        RuntimeError: If google_oauth.json is missing.
    """
    creds_dir = PROJECT_ROOT / "credentials"
    oauth_path = creds_dir / "google_oauth.json"
    token_path = creds_dir / "token.json"

    if not oauth_path.exists():
        raise RuntimeError(
            f"OAuth client config not found: {oauth_path}\n"
            f"Download it from Google Cloud Console:\n"
            f"  1. Go to console.cloud.google.com\n"
            f"  2. APIs & Services → Credentials\n"
            f"  3. Create OAuth 2.0 Client ID (Desktop app)\n"
            f"  4. Download JSON → save as {oauth_path}"
        )

    if not token_path.exists():
        logger.info(
            f"token.json not found at {token_path}. "
            f"This is expected on first run.\n"
            f"Run: python auth_flow.py\n"
            f"to complete the one-time OAuth browser login "
            f"and generate token.json."
        )
    else:
        logger.debug(f"OAuth token found: {token_path}")


async def run_all_checks(config: dict[str, Any]) -> bool:
    """Execute all startup checks in sequence.

    Args:
        config: Loaded config dict (from load_config).

    Returns:
        True if ALL checks pass, False if any critical check fails.
        Non-critical checks (disk space, token.json) log warnings
        but don't cause a False return.
    """
    checks: list[dict[str, Any]] = [
        {
            "name": "FFmpeg + libass",
            "fn": lambda: check_ffmpeg_libass(),
            "critical": True,
            "is_async": True,
        },
        {
            "name": "Disk space",
            "fn": lambda: check_disk_space(
                config.get("health_checks", {}).get(
                    "min_free_disk_gb", 2
                )
            ),
            "critical": False,
            "is_async": False,
        },
        {
            "name": "Environment variables",
            "fn": lambda: check_env_variables(),
            "critical": True,
            "is_async": False,
        },
        {
            "name": "OAuth credentials",
            "fn": lambda: check_credentials_exist(),
            "critical": True,
            "is_async": False,
        },
    ]

    all_passed = True

    for check in checks:
        name = check["name"]
        start = time.perf_counter()

        try:
            if check["is_async"]:
                await check["fn"]()
            else:
                check["fn"]()

            elapsed = (time.perf_counter() - start) * 1000
            logger.info(f"  ✓ {name} — PASS ({elapsed:.0f}ms)")

        except RuntimeError as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(f"  ✗ {name} — FAIL ({elapsed:.0f}ms)")
            logger.error(f"    {e}")

            if check["critical"]:
                all_passed = False

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(
                f"  ✗ {name} — UNEXPECTED ERROR ({elapsed:.0f}ms)"
            )
            logger.error(f"    {type(e).__name__}: {e}")
            all_passed = False

    return all_passed
