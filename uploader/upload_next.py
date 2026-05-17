import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Also add uploader/ directory so youtube_upload is found
UPLOADER_DIR = Path(__file__).resolve().parent
if str(UPLOADER_DIR) not in sys.path:
    sys.path.insert(0, str(UPLOADER_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from filelock import FileLock

# Now these imports will work regardless of working directory
from uploader.youtube_upload import (
    check_oauth_health, 
    upload_video, 
    validate_video_file, 
    load_credentials
)
from agent.alerts import alert_upload_failure
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = PROJECT_ROOT / "queue.json"
ARCHIVE_DIR = PROJECT_ROOT / "archive"

def run_upload_next():
    """Upload the next pending video from queue.json."""
    logger.info("Starting upload_next.py job...")
    
    lock_file = str(QUEUE_PATH) + ".lock"
    
    # 1. Read queue.json
    pending_entry = None
    queue_data = []
    
    with FileLock(lock_file):
        if not QUEUE_PATH.exists():
            logger.info("No queue.json found. Exiting cleanly.")
            return

        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            try:
                queue_data = json.load(f)
            except json.JSONDecodeError:
                queue_data = []
                
        # 2. Find first entry with status="pending"
        for entry in queue_data:
            if isinstance(entry, dict) and entry.get("status") == "pending":
                pending_entry = entry
                break
                
    # 3. If none found: log "No pending videos" and exit cleanly
    if not pending_entry:
        logger.info("No pending videos found in queue. Exiting cleanly.")
        return
        
    entry_id = pending_entry.get("id", "UNKNOWN")
    video_path = pending_entry.get("video_path")
    title = pending_entry.get("title", "Untitled")
    description = pending_entry.get("description", "")
    tags = pending_entry.get("tags", [])
    
    logger.info(f"Found pending video: {entry_id} -> {title}")
    
    # 4. Validates the video file
    if not video_path or not validate_video_file(video_path):
        _handle_failure(queue_data, entry_id, lock_file, f"Video validation failed for path: {video_path}", title)
        sys.exit(1)
        
    # 5. Checks OAuth health
    if not check_oauth_health():
        logger.error("OAuth health check failed. Aborting upload.")
        sys.exit(1)
        
    # 6. Uploads via upload_video()
    try:
        credentials = load_credentials()
        
        video_id = upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            credentials=credentials
        )
        
        # 7. On success: update queue, move file, log URL
        _handle_success(queue_data, entry_id, lock_file, video_id, video_path)
        
    except Exception as e:
        # 8. On failure: update queue, alert, exit
        error_msg = f"Upload failed: {str(e)}"
        _handle_failure(queue_data, entry_id, lock_file, error_msg, title)
        sys.exit(1)


def _handle_success(queue_data: list, entry_id: str, lock_file: str, video_id: str, video_path: str):
    """Handle successful upload: update queue and move file to archive."""
    # Move video file to archive
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    video_file = Path(video_path)
    if video_file.exists():
        archive_path = ARCHIVE_DIR / video_file.name
        shutil.move(str(video_file), str(archive_path))
        logger.info(f"Moved uploaded video to: {archive_path}")
        
    # Update queue entry
    with FileLock(lock_file):
        # We need to reload just in case it changed while uploading
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            current_queue = json.load(f)
            
        for entry in current_queue:
            if isinstance(entry, dict) and entry.get("id") == entry_id:
                entry["status"] = "uploaded"
                entry["youtube_video_id"] = video_id
                entry["uploaded_at"] = datetime.now(timezone.utc).isoformat()
                
                # Also update history.json
                from agent.history import HISTORY_PATH
                import json as json_lib
                if HISTORY_PATH.exists():
                    try:
                        with open(HISTORY_PATH, "r", encoding="utf-8") as hf:
                            history = json_lib.load(hf)
                        for h_entry in history:
                            if h_entry.get("run_id") == entry_id:
                                h_entry["youtube_video_id"] = video_id
                                break
                        temp_h = HISTORY_PATH.with_suffix(".tmp")
                        with open(temp_h, "w", encoding="utf-8") as hf:
                            json_lib.dump(history, hf, indent=2)
                        os.replace(temp_h, HISTORY_PATH)
                    except Exception as e:
                        logger.error(f"Failed to update history: {e}")
                
                break
                
        _atomic_write_queue(current_queue)
        

def _handle_failure(queue_data: list, entry_id: str, lock_file: str, error_message: str, title: str = "Unknown"):
    """Handle upload failure: update queue, alert telegram, exit."""
    logger.error(error_message)
    
    # NOTE: asyncio.run() used here because this function 
    # is synchronous. If ever called from async context, 
    # replace with: await alert_upload_failure(...)
    asyncio.run(alert_upload_failure(title, error_message))
    
    with FileLock(lock_file):
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            current_queue = json.load(f)
            
        for entry in current_queue:
            if isinstance(entry, dict) and entry.get("id") == entry_id:
                entry["status"] = "failed"
                entry["error_message"] = error_message
                break
                
        _atomic_write_queue(current_queue)


def _atomic_write_queue(data: list):
    """Safely write to queue.json using atomic replace."""
    temp_file = QUEUE_PATH.with_suffix('.tmp')
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_file, QUEUE_PATH)


if __name__ == "__main__":
    run_upload_next()
