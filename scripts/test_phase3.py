"""Phase 3 Test — Full Autonomous LangGraph Pipeline.

Runs one complete autonomous cycle using the LangGraph orchestrator.
No hardcoded inputs: Gemini picks the topic, writes the script, etc.
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

from dotenv import load_dotenv
load_dotenv(Path(_PROJECT_ROOT) / ".env")

from agent.config import load_config
from agent.startup_checks import run_all_checks
from agent.orchestrator import run_pipeline

# Configure basic logging for the test
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("=" * 60)
    logger.info("PHASE 3 TEST: AUTONOMOUS GRAPH PIPELINE")
    logger.info("=" * 60)

    # 1. Load config and check environment
    config = load_config()
    checks_passed = await run_all_checks(config)
    if not checks_passed:
        logger.error("Startup checks failed. Aborting Phase 3 test.")
        sys.exit(1)

    # Inject a dummy upload time for the test to avoid queue_manager warnings
    IST = timezone(timedelta(hours=5, minutes=30))
    dummy_dt = datetime.now(IST).replace(hour=18, minute=0, second=0, microsecond=0)
    config["_current_upload_dt"] = dummy_dt.isoformat()

    # 2. Run the graph pipeline
    logger.info("\n[test] Starting LangGraph pipeline run_pipeline()...")
    state = await run_pipeline(config)

    # 3. Print state summary
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE STATE SUMMARY")
    logger.info("=" * 60)
    
    # Safely get values with defaults
    run_id = state.get("run_id", "N/A")
    topic = state.get("topic", "N/A")
    char_a = state.get("character_a", "N/A")
    char_b = state.get("character_b", "N/A")
    script_count = state.get("script_line_count", 0)
    audio_dur = state.get("full_audio_duration_ms", 0.0)
    final_video = state.get("final_video", "N/A")
    is_valid = state.get("video_validated", False)
    title = state.get("title", "N/A")
    hashtags = state.get("hashtags", [])
    upload_slot = state.get("scheduled_upload_time", "N/A")
    error = state.get("error")
    failed_node = state.get("failed_node")

    logger.info(f"Run ID:                {run_id}")
    logger.info(f"Topic Chosen:          {topic}")
    logger.info(f"Characters:            {char_a} vs {char_b}")
    logger.info(f"Script Line Count:     {script_count}")
    logger.info(f"Audio Duration:        {audio_dur:.0f} ms")
    logger.info(f"Final Video Path:      {final_video}")
    logger.info(f"Video Validated:       {is_valid}")
    logger.info(f"Title Generated:       {title}")
    logger.info(f"Hashtag Count:         {len(hashtags)}")
    logger.info(f"Upload Slot Assigned:  {upload_slot}")
    
    if error:
        logger.info(f"Error:                 {error}")

    logger.info("=" * 60)

    # 4. Final success/failure evaluation
    if error:
        logger.error(f"❌ Failed at node: {failed_node}")
        logger.error(f"Error: {error}")
        sys.exit(1)
    elif is_valid:
        logger.info("✅ Phase 3 complete — full autonomous run succeeded")
        logger.info(f"Video: {final_video}")
    else:
        logger.warning("⚠️ Pipeline finished but video was not validated.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
