import json
import logging
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from tenacity import retry, stop_after_attempt, retry_if_exception, wait_exponential

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = PROJECT_ROOT / "credentials" / "google_oauth.json"
TOKEN_PATH = PROJECT_ROOT / "credentials" / "token.json"
QUEUE_PATH = PROJECT_ROOT / "queue.json"


def _send_telegram_alert(message: str) -> None:
    """Send a telegram alert if configured."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        return
    import urllib.request
    import urllib.parse
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=10)
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")


def load_credentials() -> Credentials:
    """Load token.json and refresh if expired."""
    if not TOKEN_PATH.exists():
        raise RuntimeError("token.json not found. Run auth_flow.py first.")

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token
            TOKEN_PATH.write_text(creds.to_json())
            logger.info("OAuth token refreshed successfully.")
        except Exception as e:
            raise RuntimeError(
                f"Failed to refresh OAuth token: {e}\n"
                f"Please run auth_flow.py again to re-authenticate."
            ) from e
    elif creds.expired:
        raise RuntimeError("OAuth token expired and no refresh token available. Run auth_flow.py again.")
        
    return creds


def check_oauth_health() -> bool:
    """Check if credentials are valid and monitor expiry."""
    try:
        creds = load_credentials()
        
        # Check expiry
        if creds.expiry:
            # expiry is a datetime object, usually UTC without timezone info
            expiry_dt = creds.expiry.replace(tzinfo=timezone.utc)
            now_dt = datetime.now(timezone.utc)
            time_left = expiry_dt - now_dt
            
            if time_left < timedelta(hours=48):
                logger.warning(f"OAuth token expiring within 48 hours (at {expiry_dt}). Auto-refresh should handle it.")
                
        return True
    except Exception as e:
        logger.error(f"OAuth health check failed: {e}")
        _send_telegram_alert(f"🚨 YT Autonomous Bot: OAuth token invalid or refresh failed.\nError: {e}")
        return False


def _is_retryable_error(exception: BaseException) -> bool:
    """Determine if we should retry the upload based on the exception."""
    # Never retry on client errors (400, 401, 403, 409)
    if isinstance(exception, HttpError):
        if exception.resp.status in (400, 401, 403, 409):
            return False
        # Retry on 5xx errors
        if exception.resp.status >= 500:
            return True
            
    # Retry on network/connection issues
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return True
        
    return False


@retry(
    stop=stop_after_attempt(2), # Max retries: 1 (initial attempt + 1 retry)
    retry=retry_if_exception(_is_retryable_error),
    wait=wait_exponential(multiplier=1, min=10, max=60),
    reraise=True
)
def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    credentials: Credentials
) -> str:
    """Upload video to YouTube."""
    # Truncate title to max 100 characters
    if len(title) > 100:
        title = title[:97] + "..."
        
    youtube = build("youtube", "v3", credentials=credentials)
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "28", # Science & Technology
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }
    
    # Upload video
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    logger.info(f"Starting YouTube upload for: {title}")
    response = request.execute()
    
    video_id = response.get("id")
    if not video_id:
        raise RuntimeError("Upload completed but no video ID was returned.")
        
    # Log success
    url = f"https://youtube.com/shorts/{video_id}"
    logger.info(f"✅ Upload successful! Video ID: {video_id}")
    logger.info(f"URL: {url}")
    
    # Quota tracking estimation
    uploads_today = 1 # fallback
    if QUEUE_PATH.exists():
        try:
            with open(QUEUE_PATH, "r", encoding="utf-8") as f:
                queue_data = json.load(f)
                today_str = datetime.now().date().isoformat()
                uploads_today = sum(
                    1 for entry in queue_data  # iterate list directly
                    if isinstance(entry, dict)
                    and entry.get("status") == "uploaded"
                    and entry.get("uploaded_at", "").startswith(today_str)
                ) + 1  # +1 for this current upload
        except Exception:
            pass
            
    estimated_quota_used = 1600
    estimated_remaining = 10000 - (uploads_today * estimated_quota_used)
    
    logger.info(f"Quota used: {estimated_quota_used} units.")
    logger.info(f"Estimated remaining today: {estimated_remaining} units ({uploads_today} uploads today).")
    
    return video_id


def validate_video_file(video_path: str) -> bool:
    """Validate that the file exists, is >1MB, and has video/audio streams."""
    path = Path(video_path)
    
    if not path.exists():
        logger.error(f"Validation failed: File does not exist -> {path}")
        return False
        
    if path.stat().st_size < 1024 * 1024:
        logger.error(f"Validation failed: File too small (<1MB) -> {path}")
        return False
        
    # Check streams with ffprobe
    from agent.utils import find_ffprobe
    try:
        ffprobe = find_ffprobe()
        cmd = [
            ffprobe,
            "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "json",
            str(path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        streams = [s.get("codec_type") for s in data.get("streams", [])]
        if "video" not in streams:
            logger.error(f"Validation failed: No video stream found -> {path}")
            return False
        if "audio" not in streams:
            logger.error(f"Validation failed: No audio stream found -> {path}")
            return False
            
    except Exception as e:
        logger.error(f"Validation failed during ffprobe check: {e}")
        return False
        
    return True
