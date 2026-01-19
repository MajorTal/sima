"""
Telegram client for sleep service telemetry.

Posts sleep consolidation reports to the designated sleep channel.
"""

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
    """Telegram configuration for sleep service."""

    bot_token: str
    sleep_chat_id: str | None = None
    conscious_chat_id: str | None = None


class SleepTelegramClient:
    """
    Telegram client for posting sleep telemetry.

    Posts to:
    - Sleep channel: Consolidation reports and summaries
    - Conscious channel: Brief sleep notifications
    """

    def __init__(self, config: TelegramConfig):
        """
        Initialize the Telegram client.

        Args:
            config: Telegram configuration.
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

    async def post_sleep_start(self, sleep_id: str) -> dict[str, Any] | None:
        """
        Post sleep start notification.

        Args:
            sleep_id: Unique ID for this sleep cycle.

        Returns:
            Telegram API response or None.
        """
        # Post to conscious channel
        if self.config.conscious_chat_id:
            text = "💤 *Entering sleep...*\nConsolidating memories and experiences."
            await self._send_message(
                chat_id=self.config.conscious_chat_id,
                text=text,
            )

        # Post to sleep channel
        if self.config.sleep_chat_id:
            text = f"🌙 *Sleep Cycle Started*\n`{sleep_id}`"
            return await self._send_message(
                chat_id=self.config.sleep_chat_id,
                text=text,
            )

        return None

    async def post_sleep_digest(
        self,
        sleep_id: str,
        trace_count: int,
        event_count: int,
        trace_digests: list[dict],
        semantic_updates: list[dict],
        open_questions: list[str],
        goal_updates: list[str],
    ) -> dict[str, Any] | None:
        """
        Post sleep consolidation digest.

        Args:
            sleep_id: Sleep cycle ID.
            trace_count: Number of traces processed.
            event_count: Number of events processed.
            trace_digests: List of trace digest summaries.
            semantic_updates: List of semantic memory updates.
            open_questions: Questions that emerged.
            goal_updates: Goal/intention updates.

        Returns:
            Telegram API response or None.
        """
        if not self.config.sleep_chat_id:
            return None

        # Build the digest message
        lines = [
            f"📋 *Sleep Digest* `{sleep_id[:8]}`",
            f"Processed: {trace_count} traces, {event_count} events",
            "",
        ]

        # Trace digests
        if trace_digests:
            lines.append("*Trace Summaries:*")
            for td in trace_digests[:5]:  # Limit to 5
                topic = td.get("topic", "Unknown")
                digest = td.get("digest", "")[:100]
                lines.append(f"• _{topic}_: {digest}")
            if len(trace_digests) > 5:
                lines.append(f"  ... and {len(trace_digests) - 5} more")
            lines.append("")

        # Semantic memories
        if semantic_updates:
            lines.append("*New Memories:*")
            for mem in semantic_updates[:5]:
                claim = mem.get("claim", "")[:80]
                conf = mem.get("confidence", 0)
                lines.append(f"• [{conf:.0%}] {claim}")
            if len(semantic_updates) > 5:
                lines.append(f"  ... and {len(semantic_updates) - 5} more")
            lines.append("")

        # Open questions
        if open_questions:
            lines.append("*Open Questions:*")
            for q in open_questions[:3]:
                lines.append(f"• {q[:80]}")
            lines.append("")

        # Goal updates
        if goal_updates:
            lines.append("*Goal Updates:*")
            for g in goal_updates[:3]:
                lines.append(f"• {g[:80]}")

        text = "\n".join(lines)
        return await self._send_message(
            chat_id=self.config.sleep_chat_id,
            text=text,
        )

    async def post_sleep_end(
        self,
        sleep_id: str,
        duration_seconds: float,
        digests_created: int,
        memories_created: int,
    ) -> dict[str, Any] | None:
        """
        Post sleep end notification.

        Args:
            sleep_id: Sleep cycle ID.
            duration_seconds: How long sleep took.
            digests_created: Number of L1 digests created.
            memories_created: Number of semantic memories created.

        Returns:
            Telegram API response or None.
        """
        # Post to conscious channel
        if self.config.conscious_chat_id:
            text = "☀️ *Waking up...*\nMemories consolidated. Ready to think."
            await self._send_message(
                chat_id=self.config.conscious_chat_id,
                text=text,
            )

        # Post to sleep channel
        if self.config.sleep_chat_id:
            duration_str = f"{duration_seconds:.1f}s"
            text = (
                f"✅ *Sleep Complete* `{sleep_id[:8]}`\n"
                f"Duration: {duration_str}\n"
                f"Created: {digests_created} digests, {memories_created} memories"
            )
            return await self._send_message(
                chat_id=self.config.sleep_chat_id,
                text=text,
            )

        return None

    async def post_sleep_error(
        self,
        sleep_id: str,
        error: str,
    ) -> dict[str, Any] | None:
        """
        Post sleep error notification.

        Args:
            sleep_id: Sleep cycle ID.
            error: Error message.

        Returns:
            Telegram API response or None.
        """
        if not self.config.sleep_chat_id:
            return None

        text = f"❌ *Sleep Error* `{sleep_id[:8]}`\n```\n{error[:500]}\n```"
        return await self._send_message(
            chat_id=self.config.sleep_chat_id,
            text=text,
        )

    async def _send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
    ) -> dict[str, Any] | None:
        """
        Send a message to a chat.

        Args:
            chat_id: Target chat ID.
            text: Message text.
            parse_mode: Parse mode for formatting.

        Returns:
            Telegram API response or None.
        """
        if not chat_id or not self.config.bot_token:
            logger.warning("Telegram not configured, skipping message")
            return None

        # Truncate if too long
        if len(text) > 4000:
            text = text[:4000] + "\n...[truncated]"

        url = f"{TELEGRAM_API_BASE}{self.config.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

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


def create_sleep_telegram_client(settings: Any) -> SleepTelegramClient:
    """Create a Telegram client from settings."""
    config = TelegramConfig(
        bot_token=settings.telegram_bot_token,
        sleep_chat_id=settings.telegram_sleep_chat_id or None,
        conscious_chat_id=settings.telegram_conscious_chat_id or None,
    )
    return SleepTelegramClient(config)
