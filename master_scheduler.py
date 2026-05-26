"""SaaS Master Scheduler.

This script runs 24/7 on the server.
It orchestrates the entire multi-tenant pipeline:
1. Every day at 01:00 AM, it finds all users who have connected YouTube and configured their topics.
2. It runs `agent/run_generation.py` for each user to generate their videos for the day.
3. Every 15 minutes, it runs `uploader/upload_next.py` to check the queue and upload any pending videos.

Usage:
  python master_scheduler.py
"""

import asyncio
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is on sys.path
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

from agent.supabase_bridge import get_supabase_client

async def run_daily_generation():
    """Find all active users and run the pipeline for them."""
    logger.info("=== STARTING DAILY SAAS GENERATION ===")
    
    try:
        sb = get_supabase_client()
        
        # 1. Get users who have connected YouTube
        yt_res = sb.table("youtube_connections").select("user_id").execute()
        valid_users = {row["user_id"] for row in yt_res.data}
        
        # 2. Get active user configs
        cfg_res = sb.table("user_configs").select("user_id, is_active").execute()
        
        for cfg in cfg_res.data:
            user_id = cfg["user_id"]
            if user_id not in valid_users:
                continue
                
            if cfg.get("is_active"):
                logger.warning(f"Skipping user {user_id[:8]} — already active/running.")
                continue
                
            logger.info(f"Launching generation for user {user_id[:8]}...")
            
            # Run the generation script as a subprocess with USER_ID set
            env = os.environ.copy()
            env["USER_ID"] = user_id
            
            # We use subprocess to isolate memory and prevent LangGraph state bleed between users
            cmd = [sys.executable, "agent/run_generation.py"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(PROJECT_ROOT)
            )
            
            # Stream output
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                print(f"[User {user_id[:8]}] {line.decode().rstrip()}")
                
            await process.wait()
            logger.info(f"Finished generation for user {user_id[:8]} with code {process.returncode}")
            
    except Exception as e:
        logger.error(f"Daily generation loop failed: {e}")
        
    logger.info("=== FINISHED DAILY SAAS GENERATION ===")

async def run_uploader():
    """Run the upload_next script to process the queue."""
    logger.info("Checking upload queue...")
    
    cmd = [sys.executable, "uploader/upload_next.py"]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(PROJECT_ROOT)
    )
    
    stdout, _ = await process.communicate()
    output = stdout.decode().strip()
    if "No pending videos found" not in output:
        logger.info(f"[Uploader] {output}")

async def main():
    logger.info("SaaS Master Scheduler started. Press Ctrl+C to exit.")
    
    last_generation_day = None
    
    while True:
        now = datetime.now()
        
        # Run daily generation at 01:00 AM local time
        if now.hour == 1 and now.day != last_generation_day:
            last_generation_day = now.day
            await run_daily_generation()
            
        # Run uploader every 15 minutes (or as often as the loop wakes up if we change it)
        # We'll just run it every loop iteration. The script exits cleanly if empty.
        await run_uploader()
        
        # Sleep for 15 minutes
        logger.info("Sleeping for 15 minutes...")
        await asyncio.sleep(15 * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")
