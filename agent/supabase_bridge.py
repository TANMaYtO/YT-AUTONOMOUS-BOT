"""Supabase Bridge — connects the Python agent to the web dashboard.

This module fetches user configuration from Supabase instead of config.yaml,
decrypts stored YouTube OAuth tokens, and syncs video generation results
back to the database so the web dashboard can display them.

All functions use the service role key to bypass RLS.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """Create and return a Supabase client using service role credentials."""
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env"
        )

    return create_client(url, key)


def decrypt_token(encrypted: str) -> str:
    """Decrypt an AES-256-GCM encrypted token stored by the web app.

    The encrypted format is: iv_hex:authTag_hex:ciphertext_hex
    """
    key_hex = os.environ.get("TOKEN_ENCRYPTION_KEY", "").strip()
    if not key_hex:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY must be set in .env")

    parts = encrypted.split(":")
    if len(parts) != 3:
        raise ValueError(
            f"Invalid encrypted token format — expected iv:tag:data, got {len(parts)} parts"
        )

    iv = bytes.fromhex(parts[0])
    auth_tag = bytes.fromhex(parts[1])
    ciphertext = bytes.fromhex(parts[2])

    key = bytes.fromhex(key_hex)
    aesgcm = AESGCM(key)

    # AES-GCM expects ciphertext + tag concatenated
    decrypted = aesgcm.decrypt(iv, ciphertext + auth_tag, None)
    return decrypted.decode("utf-8")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def fetch_user_config(user_id: str) -> dict[str, Any]:
    """Fetch user config from Supabase and format it like config.yaml."""
    logger.info(f"[supabase_bridge] Fetching config for user {user_id[:8]}...")

    sb = get_supabase_client()

    # Fetch user_configs
    config_res = sb.table("user_configs").select("*").eq("user_id", user_id).single().execute()
    if not config_res.data:
        raise RuntimeError(f"No user_configs row found for user {user_id[:8]}")

    cfg = config_res.data

    # Fetch plan
    plan_res = sb.table("plans").select("plan_type, videos_per_day_limit").eq("user_id", user_id).single().execute()
    plan = plan_res.data if plan_res.data else {"plan_type": "free", "videos_per_day_limit": 1}

    # Transform characters from web format to pipeline format
    raw_characters = cfg.get("characters") or []
    pipeline_characters = []
    for char in raw_characters:
        name = char.get("name", "Unknown")
        role = char.get("role", "explainer").lower()
        pipeline_characters.append({
            "name": name,
            "show": "Custom",
            "role": role,
            "voice": char.get("voice", "am_puck"),
            "image_folder": f"assets/characters/{name.replace(' ', '')}/",
        })

    # Ensure at least 2 characters with required roles
    if len(pipeline_characters) < 2:
        pipeline_characters = [
            {"name": "Nexus", "show": "Custom", "role": "explainer", "voice": "am_puck", "image_folder": "assets/characters/Nexus/"},
            {"name": "Echo", "show": "Custom", "role": "confused", "voice": "bm_george", "image_folder": "assets/characters/Echo/"},
        ]

    # Get topics
    topics = cfg.get("topics") or ["What is AI?"]

    # Get schedule
    videos_per_day = cfg.get("videos_per_day") or plan.get("videos_per_day_limit", 1)
    upload_times = cfg.get("upload_times") or ["09:00"]

    # Map niche to YouTube category ID
    niche = (cfg.get("niche") or "TECH & AI").upper()
    niche_map = {
        "TECH & AI": "28",
        "TECH": "28",
        "SCIENCE": "28",
        "GAMING": "20",
        "ANIME": "1",
        "FINANCE": "25",
        "HISTORY": "27",
    }
    category_id = niche_map.get(niche, "24")

    # Build config dict in the exact format the pipeline expects
    config: dict[str, Any] = {
        "pipeline": {
            "videos_per_day": videos_per_day,
            "generation_time": "01:00",
            "upload_slots": upload_times,
            "tts_engine": "kokoro",
            "tts_speed": 1.0,
            "category_id": category_id,
        },
        "characters": pipeline_characters,
        "topics": topics,
        "video": {
            "resolution_width": 1080,
            "resolution_height": 1920,
            "fps": 30,
            "target_duration_sec": 45,
            "background_music_volume_db": -20,
        },
        "subtitle": {
            "font": "Arial",
            "font_size": 72,
            "primary_color": "&H00FFFF00",
            "outline_color": "&H00000000",
            "outline_width": 3,
            "bold": 1,
            "alignment": 5,
            "margin_v": 0,
            "words_per_chunk": 1,
        },
        "paths": {
            "backgrounds": "assets/backgrounds/",
            "music": "assets/music/",
            "temp": "assets/temp/",
            "output": "output/",
            "archive": "archive/",
            "logs": "logs/",
            "characters": "assets/characters/",
            "queue": "queue.json",
            "history": "history.json",
            "credentials": "credentials/",
            "kokoro_model": "models/kokoro/kokoro-v1.0.onnx",
            "kokoro_voices": "models/kokoro/voices-v1.0.bin",
        },
        "ffmpeg": {
            "libass_check": True,
            "intermediate_codec": "libx264",
            "final_codec": "libx264",
            "audio_codec": "aac",
        },
        "health_checks": {
            "min_free_disk_gb": 2,
            "oauth_warning_days": 2,
        },
    }

    logger.info(
        f"[supabase_bridge] Config built: {len(pipeline_characters)} chars, "
        f"{len(topics)} topics, {videos_per_day} vids/day, "
        f"plan={plan.get('plan_type', 'free')}"
    )

    return config


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def fetch_youtube_credentials(user_id: str) -> dict[str, Any]:
    """Fetch and decrypt YouTube OAuth tokens from Supabase."""
    logger.info(f"[supabase_bridge] Fetching YouTube credentials for {user_id[:8]}...")

    sb = get_supabase_client()

    yt_res = sb.table("youtube_connections").select(
        "access_token, refresh_token, token_expiry, channel_id"
    ).eq("user_id", user_id).single().execute()

    if not yt_res.data:
        raise RuntimeError(
            f"No YouTube connection found for user {user_id[:8]}. "
            f"Please connect YouTube via the web dashboard first."
        )

    row = yt_res.data
    access_token = decrypt_token(row["access_token"]) if row.get("access_token") else None
    refresh_token = decrypt_token(row["refresh_token"]) if row.get("refresh_token") else None

    if not access_token:
        raise RuntimeError("YouTube access token is missing or could not be decrypted.")

    logger.info(f"[supabase_bridge] YouTube credentials decrypted for channel {row.get('channel_id', 'unknown')}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expiry": row.get("token_expiry"),
        "channel_id": row.get("channel_id"),
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def sync_video_to_supabase(
    user_id: str,
    state: dict[str, Any],
    status: str = "pending",
) -> str:
    """Insert or update a video record in the Supabase videos table."""
    logger.info(f"[supabase_bridge] Syncing video {state.get('run_id', '?')[:8]} as '{status}'")

    sb = get_supabase_client()

    video_data = {
        "user_id": user_id,
        "run_id": state.get("run_id"),
        "title": state.get("title"),
        "topic": state.get("topic"),
        "character_a": state.get("character_a"),
        "character_b": state.get("character_b"),
        "status": status,
        "scheduled_upload_time": state.get("scheduled_upload_time"),
        "storage_key": state.get("storage_key"),
        "video_path": str(state.get("final_video", "")) if state.get("final_video") else None,
        "error_message": state.get("error") if status == "failed" else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    res = sb.table("videos").upsert(
        video_data, on_conflict="run_id"
    ).execute()

    video_id = res.data[0]["id"] if res.data else "unknown"
    logger.info(f"[supabase_bridge] Video synced: id={video_id}")
    return video_id


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def update_video_status(
    run_id: str,
    status: str,
    youtube_video_id: str | None = None,
    youtube_url: str | None = None,
    error_message: str | None = None,
) -> None:
    """Update a video row's status after upload attempt."""
    logger.info(f"[supabase_bridge] Updating video {run_id[:8]} → {status}")

    sb = get_supabase_client()

    update_data: dict[str, Any] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if youtube_video_id:
        update_data["youtube_video_id"] = youtube_video_id
    if youtube_url:
        update_data["youtube_url"] = youtube_url
    if error_message:
        update_data["error_message"] = error_message[:500]

    sb.table("videos").update(update_data).eq("run_id", run_id).execute()
    logger.info(f"[supabase_bridge] Video status updated successfully")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def mark_agent_active(user_id: str, active: bool = True) -> None:
    """Update the agent's active status and last_run_at timestamp."""
    logger.info(f"[supabase_bridge] Setting agent active={active} for {user_id[:8]}")

    sb = get_supabase_client()

    sb.table("user_configs").update({
        "is_active": active,
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", user_id).execute()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def update_youtube_access_token(
    user_id: str,
    new_access_token: str,
    new_expiry_iso: str,
) -> None:
    """Encrypt and persist a refreshed access token back to Supabase."""
    logger.info(f"[supabase_bridge] Writing refreshed token for {user_id[:8]}...")

    key_hex = os.environ.get("TOKEN_ENCRYPTION_KEY", "").strip()
    if not key_hex:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY must be set in .env")

    import secrets
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = bytes.fromhex(key_hex)
    aesgcm = AESGCM(key)
    iv = secrets.token_bytes(12)
    ciphertext_and_tag = aesgcm.encrypt(iv, new_access_token.encode("utf-8"), None)
    # Split: last 16 bytes are the GCM auth tag
    ciphertext = ciphertext_and_tag[:-16]
    auth_tag = ciphertext_and_tag[-16:]
    encrypted = f"{iv.hex()}:{auth_tag.hex()}:{ciphertext.hex()}"

    sb = get_supabase_client()
    sb.table("youtube_connections").update({
        "access_token": encrypted,
        "token_expiry": new_expiry_iso,
    }).eq("user_id", user_id).execute()

    logger.info(f"[supabase_bridge] Refreshed access token persisted for {user_id[:8]}")
