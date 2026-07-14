import os
import json
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
from supabase import create_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate():
    # Hardcoded credentials for one-off script
    SUPABASE_URL = "https://qwnzpiptxwktcxkzlsjd.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF3bnpwaXB0eHdrdGN4a3psc2pkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTUyNzM3MSwiZXhwIjoyMDk1MTAzMzcxfQ.bFHyX5m0wq6fHPtbhK-Asf7MAdwRdvz68998U7WXkjk"
    
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get the user_id from the database
    res = sb.table("user_configs").select("user_id").limit(1).execute()
    if not res.data:
        logger.error("No users found in database.")
        return
        
    user_id = res.data[0]["user_id"]
    logger.info(f"Found user_id: {user_id}")

    history_path = PROJECT_ROOT / "history.json"
    if not history_path.exists():
        logger.error("history.json not found.")
        return

    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read history.json: {e}")
        return


    success_count = 0
    for entry in history:
        run_id = entry.get("run_id")
        video_id = entry.get("youtube_video_id")
        status = "uploaded" if video_id else "failed"
        
        video_data = {
            "user_id": user_id,
            "run_id": run_id,
            "title": entry.get("title", "Untitled"),
            "topic": entry.get("topic", "Unknown"),
            "character_a": entry.get("character_a"),
            "character_b": entry.get("character_b"),
            "status": status,
            "youtube_video_id": video_id,
            "youtube_url": f"https://youtube.com/shorts/{video_id}" if video_id else None,
            # For backfilled data, use the date provided or now
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            sb.table("videos").upsert(video_data, on_conflict="run_id").execute()
            success_count += 1
            logger.info(f"Migrated video: {run_id}")
        except Exception as e:
            logger.error(f"Failed to migrate video {run_id}: {e}")

    logger.info(f"Successfully migrated {success_count} videos for user {user_id}.")

if __name__ == "__main__":
    asyncio.run(migrate())
