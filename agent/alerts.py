import logging
import os
import httpx

logger = logging.getLogger(__name__)

async def send_telegram_alert(message: str) -> None:
    """Send a failure alert via Telegram Bot API.
    
    Silently does nothing if Telegram is not configured.
    Never raises — alerting must never crash the pipeline.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    if not bot_token or not chat_id:
        logger.debug("Telegram not configured — skipping alert")
        return
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": message}
            )
    except Exception as e:
        logger.warning(f"Telegram alert failed to send: {e}")

async def alert_pipeline_failure(
    run_id: str,
    failed_node: str, 
    error: str
) -> None:
    """Send formatted pipeline failure alert."""
    message = (
        f"🚨 YT Shorts Agent — Pipeline Failed\n"
        f"Run ID: {run_id}\n"
        f"Failed at: {failed_node}\n"
        f"Error: {error[:200]}"  # truncate long errors
    )
    await send_telegram_alert(message)

async def alert_upload_failure(
    title: str,
    error: str
) -> None:
    """Send formatted upload failure alert."""
    message = (
        f"🚨 YT Shorts Agent — Upload Failed\n"
        f"Video: {title}\n"
        f"Error: {error[:200]}"
    )
    await send_telegram_alert(message)

async def alert_oauth_expiry(expiry_time: str) -> None:
    """Warn when OAuth token is near expiry."""
    message = (
        f"⚠️ YT Shorts Agent — OAuth Warning\n"
        f"Token expiring at: {expiry_time}\n"
        f"Run auth_flow.py to refresh before it expires."
    )
    await send_telegram_alert(message)

async def alert_daily_summary(
    success_count: int,
    total: int,
    titles: list[str]
) -> None:
    """Send daily generation summary."""
    status = "✅" if success_count == total else "⚠️"
    titles_str = "\n".join(f"  • {t}" for t in titles)
    message = (
        f"{status} YT Shorts Agent — Daily Summary\n"
        f"Generated: {success_count}/{total} videos\n"
        f"Videos:\n{titles_str}"
    )
    await send_telegram_alert(message)
