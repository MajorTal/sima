"""
Telegram webhook handler.
"""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from .settings import settings
from .sqs import enqueue_telegram_update

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_telegram_secret(secret_token: str | None) -> bool:
    """
    Verify the Telegram webhook secret token.

    Args:
        secret_token: The X-Telegram-Bot-Api-Secret-Token header value.

    Returns:
        True if valid or no secret configured.
    """
    if not settings.telegram_webhook_secret:
        return True

    if not secret_token:
        return False

    return hmac.compare_digest(secret_token, settings.telegram_webhook_secret)


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict[str, str]:
    """
    Receive Telegram webhook updates.

    The endpoint receives updates from Telegram and enqueues them
    to SQS for asynchronous processing by The Brain.
    """
    # Verify webhook secret
    if not verify_telegram_secret(x_telegram_bot_api_secret_token):
        logger.warning("Invalid Telegram webhook secret")
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # Parse update
    try:
        update: dict[str, Any] = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse Telegram update: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Log update info
    update_id = update.get("update_id", "unknown")
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id", "unknown")
    text = message.get("text", "")[:50] if message.get("text") else ""

    logger.info(
        f"Received Telegram update {update_id} from chat {chat_id}: {text}..."
    )

    # Enqueue for processing
    try:
        message_id = enqueue_telegram_update(update)
        return {"status": "ok", "message_id": message_id}
    except Exception as e:
        logger.exception(f"Failed to enqueue Telegram update: {e}")
        raise HTTPException(status_code=500, detail="Failed to enqueue message")


@router.get("/webhook/info")
async def webhook_info() -> dict[str, Any]:
    """Get webhook configuration info."""
    return {
        "configured": bool(settings.telegram_bot_token),
        "queue_url": settings.sqs_queue_url[:20] + "..." if settings.sqs_queue_url else None,
    }
