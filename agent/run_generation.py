"""Daily Generation Runner.

This script is intended to be called by Windows Task Scheduler (e.g., at 1 AM).
It runs the full LangGraph pipeline N times as specified in the config,
assigns upload slots, and pauses between runs.
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load .env BEFORE importing agent modules that use env vars
from dotenv import load_dotenv
load_dotenv(Path(_PROJECT_ROOT) / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

from agent.config import load_config
from agent.startup_checks import run_all_checks
from agent.orchestrator import run_pipeline


def build_upload_datetime(time_str: str) -> str:
    """Convert '09:00' to today's ISO 8601 datetime in IST."""
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)
    hour, minute = map(int, time_str.split(":"))
    upload_dt = now.replace(
        hour=hour, 
        minute=minute,
        second=0, 
        microsecond=0
    )
    return upload_dt.isoformat()


async def main():
    # 1. Set WindowsSelectorEventLoopPolicy if needed
    # NOTE: Windows default ProactorEventLoop is required for asyncio.create_subprocess_exec (FFmpeg).
    # We do NOT set WindowsSelectorEventLoopPolicy here.

    # 2. Load config
    config = load_config()
    
    logger.info("=" * 60)
    logger.info("DAILY GENERATION RUNNER STARTED")
    logger.info("=" * 60)

    # 3. Run all startup checks
    checks_passed = await run_all_checks(config)
    if not checks_passed:
        logger.error("Startup checks failed — aborting")
        sys.exit(1)
    
    # 4. Get today's video count from config
    videos_per_day = config["pipeline"]["videos_per_day"]
    
    # 5. Get upload time slots and assign one per video
    upload_slots = config["pipeline"]["upload_slots"]
    
    # 6. Loop: run pipeline N times
    results = []
    for i in range(videos_per_day):
        logger.info(
            f"\n[daily] Generating video {i+1}/{videos_per_day}"
        )
        
        # Assign upload slot for this video
        slot = upload_slots[i % len(upload_slots)]
        
        # Build today's upload datetime from slot time string
        # e.g. "09:00" → today's date + 09:00 IST as ISO 8601
        upload_dt = build_upload_datetime(slot)
        
        # Pass the upload time into config so queue_manager can read it if needed
        config["_current_upload_dt"] = upload_dt
        
        # Run one full pipeline
        state = await run_pipeline(config)
        
        if state.get("error"):
            logger.error(f"[daily] Video {i+1} FAILED — skipping")
            results.append({
                "index": i+1, 
                "status": "failed",
                "error": state["error"]
            })
        else:
            results.append({
                "index": i+1, 
                "status": "success",
                "video": state.get("final_video"),
                "title": state.get("title"),
                "slot": slot
            })
        
        # Wait 30 seconds between videos (rate limiting + disk I/O)
        if i < videos_per_day - 1:
            logger.info("[daily] Waiting 30 seconds before next video...")
            await asyncio.sleep(30)
    
    # 7. Print daily summary
    success_count = sum(1 for r in results if r["status"] == "success")
    logger.info("\n" + "=" * 60)
    logger.info(f"[daily] Done: {success_count}/{videos_per_day} videos generated")
    logger.info("=" * 60)
    
    for r in results:
        if r["status"] == "success":
            logger.info(f"  ✅ Video {r['index']}: {r['title']} → {r['slot']}")
        else:
            logger.info(f"  ❌ Video {r['index']}: {r['error']}")


if __name__ == "__main__":
    asyncio.run(main())
