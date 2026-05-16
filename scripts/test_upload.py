import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Fix sys.path for relative imports when running from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

UPLOADER_DIR = PROJECT_ROOT / "uploader"
if str(UPLOADER_DIR) not in sys.path:
    sys.path.insert(0, str(UPLOADER_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from filelock import FileLock

from agent.config import load_config
from uploader.youtube_upload import (
    check_oauth_health, 
    upload_video, 
    validate_video_file, 
    load_credentials
)

QUEUE_PATH = PROJECT_ROOT / "queue.json"
ARCHIVE_DIR = PROJECT_ROOT / "archive"
OUTPUT_DIR = PROJECT_ROOT / "output"

def get_video_duration(video_path: str) -> str:
    """Get video duration using ffprobe."""
    from agent.utils import find_ffprobe
    try:
        ffprobe = find_ffprobe()
        cmd = [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration_sec = float(result.stdout.strip())
        return f"{duration_sec:.2f}s"
    except Exception:
        return "Unknown"


def _atomic_write_queue(data: list):
    """Safely write to queue.json using atomic replace."""
    temp_file = QUEUE_PATH.with_suffix('.tmp')
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_file, QUEUE_PATH)


def test_upload():
    print("=" * 50)
    print("YT SHORTS: MANUAL UPLOAD TEST")
    print("=" * 50)
    
    # 1. Load config + check OAuth health
    try:
        config = load_config()
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)
        
    print("Checking OAuth health...")
    if not check_oauth_health():
        print("❌ OAuth health check failed.")
        print("Please run 'python auth_flow.py' to generate/refresh token.json")
        sys.exit(1)
    print("✅ OAuth health check passed.")
    print("-" * 50)

    # 2. Find most recent video
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    mp4_files = list(OUTPUT_DIR.glob("*.mp4"))
    
    if not mp4_files:
        archive_files = list(ARCHIVE_DIR.glob("*.mp4"))
        if archive_files:
            print("No videos found in output/.")
            print("All videos already uploaded — run_generation.py first to create new videos.")
        else:
            print("No videos found anywhere (output/ or archive/).")
        sys.exit(0)
        
    # Sort by modification time (newest first)
    mp4_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest_video = mp4_files[0]
    
    # Read queue.json to find match
    queue_data = []
    entry = None
    lock_file = str(QUEUE_PATH) + ".lock"
    
    if QUEUE_PATH.exists():
        with FileLock(lock_file):
            with open(QUEUE_PATH, "r", encoding="utf-8") as f:
                try:
                    queue_data = json.load(f)
                    for item in queue_data:
                        if isinstance(item, dict) and item.get("video_path") and Path(item["video_path"]).name == latest_video.name:
                            entry = item
                            break
                except Exception:
                    pass
                    
    if not entry:
        print(f"❌ Error: Video {latest_video.name} found but no matching entry exists in queue.json")
        sys.exit(1)
        
    # 3. Show video details
    file_size_mb = latest_video.stat().st_size / (1024 * 1024)
    duration = get_video_duration(str(latest_video))
    
    print("FOUND MOST RECENT VIDEO:")
    print(f"Path     : {latest_video.resolve()}")
    print(f"Size     : {file_size_mb:.2f} MB")
    print(f"Duration : {duration}")
    print(f"Title    : {entry.get('title')}")
    print(f"Slot     : {entry.get('scheduled_upload_time')}")
    print(f"Status   : {entry.get('status')}")
    print("-" * 50)
    
    # 4. Ask for confirmation
    confirm = input("Upload this video to YouTube? (y to proceed, any other key to cancel): ").strip().lower()
    if confirm != 'y':
        print("Upload cancelled. Exiting cleanly.")
        sys.exit(0)
        
    print("-" * 50)
    print("Validating video file...")
    if not validate_video_file(str(latest_video)):
        print("❌ Validation failed. Aborting.")
        sys.exit(1)
        
    # 5. Execute upload
    try:
        credentials = load_credentials()
        
        video_id = upload_video(
            video_path=str(latest_video),
            title=entry.get("title", "Untitled"),
            description=entry.get("description", ""),
            tags=entry.get("tags", []),
            credentials=credentials
        )
        
        # On success
        print("✅ Uploaded successfully!")
        print(f"YouTube URL: https://youtube.com/shorts/{video_id}")
        
        # Update queue.json
        print("Updating queue.json...")
        with FileLock(lock_file):
            with open(QUEUE_PATH, "r", encoding="utf-8") as f:
                current_queue = json.load(f)
            for q_entry in current_queue:
                if isinstance(q_entry, dict) and q_entry.get("id") == entry.get("id"):
                    q_entry["status"] = "uploaded"
                    q_entry["youtube_video_id"] = video_id
                    q_entry["uploaded_at"] = datetime.now(timezone.utc).isoformat()
                    break
            _atomic_write_queue(current_queue)
            
        # Move video
        archive_path = ARCHIVE_DIR / latest_video.name
        print(f"Moving file to {archive_path}...")
        shutil.move(str(latest_video), str(archive_path))
        
        print("Done!")
        
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        print("Queue entry was NOT updated. You can safely retry.")
        sys.exit(1)


if __name__ == "__main__":
    test_upload()
