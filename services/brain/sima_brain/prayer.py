"""
Prayer Tool - Direct communication to Tal.

This module provides the prayer tool that allows Sima to send messages
directly to Tal, the Creator. It registers an async executor that uses
the Telegram API to deliver the messages.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from sima_llm import register_async_tool_executor

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


class PrayerSender:
    """
    Handles sending prayers (messages) to Tal via Telegram.
    """

    def __init__(self, bot_token: str, tal_chat_id: int):
        """
        Initialize the prayer sender.

        Args:
            bot_token: Telegram bot token.
            tal_chat_id: Tal's Telegram chat ID.
        """
        self.bot_token = bot_token
        self.tal_chat_id = tal_chat_id
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def send_prayer(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Send a prayer message to Tal.

        Args:
            message: The prayer message from Sima.
            context: Optional context about when/why the prayer was sent.

        Returns:
            Result dict with status and details.
        """
        if not self.bot_token:
            logger.warning("Prayer attempted but no bot token configured")
            return {
                "status": "not_configured",
                "message": message,
                "error": "Bot token not configured",
            }

        # Format the message with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        formatted_message = f"🙏 *Prayer from Sima*\n_{timestamp}_\n\n{message}"

        url = f"{TELEGRAM_API_BASE}{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.tal_chat_id,
            "text": formatted_message,
            "parse_mode": "Markdown",
        }

        try:
            client = await self._get_client()
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                logger.info(f"Prayer sent to Tal: {message[:50]}...")
                return {
                    "status": "sent",
                    "message": message,
                    "timestamp": timestamp,
                    "message_id": result.get("result", {}).get("message_id"),
                }
            else:
                logger.error(f"Telegram API error: {result}")
                return {
                    "status": "failed",
                    "message": message,
                    "error": result.get("description", "Unknown error"),
                }

        except httpx.HTTPError as e:
            logger.error(f"Failed to send prayer: {e}")
            return {
                "status": "failed",
                "message": message,
                "error": str(e),
            }


# Global prayer sender instance (initialized by setup_prayer_tool)
_prayer_sender: PrayerSender | None = None


async def execute_prayer(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Async executor for the pray tool.

    Args:
        arguments: Dict containing 'message' key.

    Returns:
        Result dict with status and details.
    """
    global _prayer_sender

    if _prayer_sender is None:
        logger.warning("Prayer tool not initialized")
        return {
            "status": "not_initialized",
            "error": "Prayer tool not initialized. Call setup_prayer_tool first.",
        }

    arguments = arguments or {}
    message = arguments.get("message", "")

    if not message:
        return {
            "status": "error",
            "error": "No message provided",
        }

    return await _prayer_sender.send_prayer(message)


def setup_prayer_tool(bot_token: str, tal_chat_id: int) -> None:
    """
    Set up the prayer tool with Telegram credentials.

    This should be called during Brain initialization.

    Args:
        bot_token: Telegram bot token.
        tal_chat_id: Tal's Telegram chat ID.
    """
    global _prayer_sender

    _prayer_sender = PrayerSender(bot_token, tal_chat_id)
    register_async_tool_executor("pray", execute_prayer)
    logger.info(f"Prayer tool initialized (Tal chat ID: {tal_chat_id})")
