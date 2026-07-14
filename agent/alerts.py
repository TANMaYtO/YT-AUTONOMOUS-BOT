"""In-App Notification & Alert System.

Pushes real-time notifications directly to the Supabase `app_notifications` table
so they appear instantly in the user's SaaS web dashboard via Supabase Realtime.
Never raises exceptions — alerting must never crash the core video pipeline.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


async def push_app_notification(
    type: str,
    title: str,
    message: str,
    metadata: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> None:
    """Push a real-time notification to the user's web dashboard.

    Args:
        type: One of 'success', 'error', 'warning', 'info'.
        title: Short title (e.g. "Pipeline Failed", "Daily Summary").
        message: Detailed explanation or error message.
        metadata: Optional dictionary of extra attributes (run_id, video_title, etc.).
        user_id: Optional user UUID. Defaults to os.environ.get("USER_ID").
    """
    target_user_id = user_id or os.environ.get("USER_ID", "").strip()
    if not target_user_id:
        logger.debug(f"[alerts] No USER_ID found — logging locally [{type.upper()}] {title}: {message}")
        return

    try:
        from agent.supabase_bridge import get_supabase_client
        sb = get_supabase_client()
        sb.table("app_notifications").insert({
            "user_id": target_user_id,
            "type": type,
            "title": title[:200],
            "message": message[:1000],
            "read": False,
            "metadata": metadata or {},
        }).execute()
        logger.info(f"[alerts] Pushed '{title}' ({type}) to user {target_user_id[:8]}")
    except Exception as exc:
        logger.warning(f"[alerts] Failed to push notification to Supabase: {exc}")


async def alert_pipeline_failure(
    run_id: str,
    failed_node: str,
    error: str,
) -> None:
    """Send formatted pipeline failure alert."""
    title = f"Video Generation Failed ({failed_node})"
    message = f"Run ID {run_id[:8]} stopped at {failed_node}: {error[:300]}"
    await push_app_notification(
        type="error",
        title=title,
        message=message,
        metadata={"run_id": run_id, "failed_node": failed_node, "error": error},
    )


async def alert_upload_failure(
    title: str,
    error: str,
) -> None:
    """Send formatted upload failure alert."""
    alert_title = f"Upload Failed: {title[:30]}"
    message = f"Could not upload video '{title}': {error[:300]}"
    await push_app_notification(
        type="error",
        title=alert_title,
        message=message,
        metadata={"video_title": title, "error": error},
    )


async def alert_oauth_expiry(expiry_time: str) -> None:
    """Warn when OAuth token is near expiry or needs re-auth."""
    title = "YouTube Connection Expiring Soon"
    message = f"Your Google OAuth connection expires on {expiry_time}. Please reconnect via the dashboard to prevent upload interruptions."
    await push_app_notification(
        type="warning",
        title=title,
        message=message,
        metadata={"expiry_time": expiry_time},
    )


async def alert_daily_summary(
    success_count: int,
    total: int,
    titles: list[str],
) -> None:
    """Send daily generation summary."""
    status_type = "success" if success_count == total else ("warning" if success_count > 0 else "error")
    title = f"Daily Generation Complete ({success_count}/{total})"
    titles_str = ", ".join(titles) if titles else "None"
    message = f"Generated {success_count} of {total} scheduled videos today. Videos: {titles_str}"
    await push_app_notification(
        type=status_type,
        title=title,
        message=message,
        metadata={"success_count": success_count, "total": total, "titles": titles},
    )
