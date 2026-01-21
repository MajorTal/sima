"""
Telegram API client for sending messages to different channels.

Supports:
- External channel: User-facing messages (Sima's voice)
- Conscious channel: Workspace state and inner monologue
- Subconscious channel: Full module outputs (JSON telemetry)
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from sima_core.types import Stream

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


@dataclass
class TelegramConfig:
    """Telegram configuration."""

    bot_token: str
    external_chat_id: str | None = None
    conscious_chat_id: str | None = None
    subconscious_chat_id: str | None = None


class TelegramClient:
    """
    Async Telegram client for sending messages to different channels.

    Each stream type maps to a different Telegram channel:
    - EXTERNAL: User-facing messages
    - CONSCIOUS: Inner monologue / workspace state
    - SUBCONSCIOUS: Full JSON telemetry
    """

    def __init__(self, config: TelegramConfig):
        """
        Initialize the Telegram client.

        Args:
            config: Telegram configuration with bot token and chat IDs.
        """
        self.config = config
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

    def _get_chat_id(self, stream: Stream) -> str | None:
        """Get the chat ID for a stream type."""
        match stream:
            case Stream.EXTERNAL:
                return self.config.external_chat_id
            case Stream.CONSCIOUS:
                return self.config.conscious_chat_id
            case Stream.SUBCONSCIOUS:
                return self.config.subconscious_chat_id
            case _:
                return None

    async def send_message(
        self,
        stream: Stream,
        text: str,
        reply_to_message_id: int | None = None,
        parse_mode: str | None = "Markdown",
    ) -> dict[str, Any] | None:
        """
        Send a text message to the appropriate channel.

        Args:
            stream: Target stream (determines which chat).
            text: Message text.
            reply_to_message_id: Optional message to reply to.
            parse_mode: Parse mode for formatting (Markdown, HTML, None).

        Returns:
            Telegram API response or None if failed.
        """
        chat_id = self._get_chat_id(stream)
        if not chat_id:
            logger.warning(f"No chat ID configured for stream {stream}")
            return None

        # Truncate if too long (Telegram limit is 4096)
        if len(text) > 4000:
            text = text[:4000] + "\n...[truncated]"

        url = f"{TELEGRAM_API_BASE}{self.config.bot_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }

        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            client = await self._get_client()
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            if not result.get("ok"):
                logger.error(f"Telegram API error: {result}")
                return None

            return result.get("result")

        except httpx.HTTPError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return None

    async def send_json(
        self,
        stream: Stream,
        data: dict[str, Any],
        label: str = "",
    ) -> dict[str, Any] | None:
        """
        Send JSON data as a formatted message.

        Args:
            stream: Target stream.
            data: JSON data to send.
            label: Optional label prefix.

        Returns:
            Telegram API response or None if failed.
        """
        # Format as code block
        json_text = json.dumps(data, indent=2, default=str)

        if label:
            text = f"*{label}*\n```json\n{json_text}\n```"
        else:
            text = f"```json\n{json_text}\n```"

        return await self.send_message(stream, text, parse_mode="Markdown")

    async def send_event(
        self,
        stream: Stream,
        event_type: str,
        actor: str,
        content: dict[str, Any] | str | None,
        trace_id: str,
    ) -> dict[str, Any] | None:
        """
        Send an event to the appropriate telemetry channel.

        Args:
            stream: Target stream.
            event_type: Type of event.
            actor: Module that produced the event.
            content: Event content (dict or string).
            trace_id: Trace ID for correlation.

        Returns:
            Telegram API response or None if failed.
        """
        short_trace = trace_id[:8]

        if stream == Stream.EXTERNAL:
            # External stream: just the message text
            if isinstance(content, dict):
                text = content.get("message", str(content))
            else:
                text = str(content) if content else ""
            return await self.send_message(stream, text, parse_mode=None)

        elif stream == Stream.CONSCIOUS:
            # Conscious stream: summary format
            if isinstance(content, dict):
                summary = content.get("workspace_summary", content.get("message", ""))
                text = f"[{short_trace}] *{actor}*\n{summary}"
            else:
                text = f"[{short_trace}] *{actor}*\n{content}"
            return await self.send_message(stream, text)

        else:
            # Subconscious stream: full JSON
            label = f"[{short_trace}] {event_type} ({actor})"
            return await self.send_json(stream, content if isinstance(content, dict) else {"text": content}, label)

    async def reply_to_user(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
    ) -> dict[str, Any] | None:
        """
        Reply directly to a user's chat.

        Args:
            chat_id: User's chat ID.
            text: Message text.
            reply_to_message_id: Original message to reply to.

        Returns:
            Telegram API response or None if failed.
        """
        url = f"{TELEGRAM_API_BASE}{self.config.bot_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }

        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        try:
            client = await self._get_client()
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            if not result.get("ok"):
                logger.error(f"Telegram API error: {result}")
                return None

            return result.get("result")

        except httpx.HTTPError as e:
            logger.error(f"Failed to send Telegram reply: {e}")
            return None


def create_telegram_client_from_settings(settings: Any) -> TelegramClient:
    """Create a Telegram client from settings."""
    config = TelegramConfig(
        bot_token=settings.telegram_bot_token,
        external_chat_id=settings.telegram_external_chat_id or None,
        conscious_chat_id=settings.telegram_conscious_chat_id or None,
        subconscious_chat_id=settings.telegram_subconscious_chat_id or None,
    )
    return TelegramClient(config)
