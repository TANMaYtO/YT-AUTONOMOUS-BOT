"""SaaS Master Scheduler.

Runs 24/7 on the server. Orchestrates the full multi-tenant pipeline:
- Every day at 01:00 AM: runs video generation for all active users CONCURRENTLY
  (up to MAX_CONCURRENT_USERS at a time via asyncio.Semaphore)
- Every 15 minutes: checks the upload queue and uploads pending videos per user
- On startup: resets any stale is_active=True locks from crashed pipelines

Usage:
  python master_scheduler.py
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

from agent.supabase_bridge import get_supabase_client, mark_agent_active

# Maximum number of users whose pipelines run concurrently.
# Increase if the server has more CPU/RAM headroom.
MAX_CONCURRENT_USERS = 5


async def reset_stale_active_flags() -> None:
    """Reset is_active=True rows stuck from crashed pipelines (older than 2 hours)."""
    try:
        two_hours_ago = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()
        sb = get_supabase_client()
        result = (
            sb.table("user_configs")
            .update({"is_active": False})
            .eq("is_active", True)
            .lt("last_run_at", two_hours_ago)
            .execute()
        )
        if result.data:
            logger.warning(
                f"[watchdog] Reset {len(result.data)} stale is_active locks "
                f"(last_run_at older than 2 hours)"
            )
    except Exception as exc:
        logger.error(f"[watchdog] Failed to reset stale locks: {exc}")


async def run_generation_for_user(
    user_id: str,
    sem: asyncio.Semaphore,
) -> int:
    """Run video generation pipeline for a single user under concurrency semaphore.

    Args:
        user_id: The Supabase user UUID.
        sem: Shared semaphore capping concurrent pipeline runs.

    Returns:
        The subprocess return code (0 = success).
    """
    async with sem:
        logger.info(f"[gen] Starting pipeline for user {user_id[:8]}...")
        env = os.environ.copy()
        env["USER_ID"] = user_id

        cmd = [sys.executable, "agent/run_generation.py"]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(PROJECT_ROOT),
            )

            assert process.stdout is not None
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                logger.info(f"[{user_id[:8]}] {line.decode().rstrip()}")

            return_code = await process.wait()
            log_level = logging.INFO if return_code == 0 else logging.ERROR
            logger.log(
                log_level,
                f"[gen] User {user_id[:8]} finished with code {return_code}",
            )
            return return_code

        except Exception as exc:
            logger.error(f"[gen] User {user_id[:8]} pipeline raised exception: {exc}")
            return -1
        finally:
            # ALWAYS reset is_active — even if pipeline crashed mid-run
            try:
                await mark_agent_active(user_id, False)
            except Exception as reset_exc:
                logger.error(
                    f"[watchdog] Failed to reset is_active for {user_id[:8]}: {reset_exc}"
                )


async def run_daily_generation() -> None:
    """Find all eligible users and run their generation pipeline concurrently."""
    logger.info("=" * 60)
    logger.info("STARTING DAILY SAAS GENERATION")
    logger.info("=" * 60)

    try:
        sb = get_supabase_client()

        yt_res = sb.table("youtube_connections").select("user_id").execute()
        users_with_yt = {row["user_id"] for row in (yt_res.data or [])}

        cfg_res = sb.table("user_configs").select("user_id, is_active").execute()
        configs = cfg_res.data or []

        eligible_users: list[str] = []
        for cfg in configs:
            user_id = cfg["user_id"]
            if user_id not in users_with_yt:
                continue
            if cfg.get("is_active"):
                logger.warning(f"Skipping {user_id[:8]} — pipeline already running")
                continue
            eligible_users.append(user_id)

        logger.info(f"[gen] {len(eligible_users)} users eligible for generation today")

        if not eligible_users:
            logger.info("[gen] No eligible users. Skipping generation.")
            return

        sem = asyncio.Semaphore(MAX_CONCURRENT_USERS)
        tasks = [
            run_generation_for_user(user_id, sem)
            for user_id in eligible_users
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(
            1 for r in results
            if isinstance(r, int) and r == 0
        )
        logger.info(
            f"[gen] Daily generation complete: "
            f"{success_count}/{len(eligible_users)} users succeeded"
        )

    except Exception as exc:
        logger.error(f"[gen] Daily generation loop crashed: {exc}")

    logger.info("=" * 60)
    logger.info("FINISHED DAILY SAAS GENERATION")
    logger.info("=" * 60)


async def run_uploader_for_user(user_id: str) -> None:
    """Run the uploader for a specific user, passing their USER_ID env var."""
    env = os.environ.copy()
    env["USER_ID"] = user_id

    cmd = [sys.executable, "uploader/upload_next.py"]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
        )
        stdout, _ = await process.communicate()
        output = stdout.decode().strip()
        if output and "No pending videos found" not in output:
            logger.info(f"[uploader][{user_id[:8]}] {output}")
    except Exception as exc:
        logger.error(f"[uploader] Failed for user {user_id[:8]}: {exc}")


async def run_all_uploaders() -> None:
    """Check upload queue for ALL users and upload any pending videos."""
    try:
        sb = get_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()
        pending_res = (
            sb.table("videos")
            .select("user_id")
            .eq("status", "pending")
            .lte("scheduled_upload_time", now_iso)
            .execute()
        )
        pending_data = pending_res.data or []
        if not pending_data:
            return

        users_with_pending = list({row["user_id"] for row in pending_data})
        logger.info(f"[uploader] {len(users_with_pending)} user(s) have videos ready to upload")

        tasks = [run_uploader_for_user(uid) for uid in users_with_pending]
        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as exc:
        logger.error(f"[uploader] Upload queue check failed: {exc}")


async def main() -> None:
    """Main scheduler loop — runs indefinitely."""
    logger.info("SaaS Master Scheduler starting up...")
    await reset_stale_active_flags()
    logger.info("Scheduler ready. Entering main loop.")

    last_generation_day: int | None = None

    while True:
        now = datetime.now()

        if now.hour == 1 and now.day != last_generation_day:
            last_generation_day = now.day
            await run_daily_generation()

        await run_all_uploaders()

        logger.info("[scheduler] Sleeping for 15 minutes...")
        await asyncio.sleep(15 * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")
