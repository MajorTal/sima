"""
SQS Worker - Consumes messages from SQS and routes to awake loop.

Handles:
- Telegram webhook events (user messages)
- Minute tick events (time-based triggers)
- Autonomous tick events (scheduled thinking triggers)
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import boto3

from sima_core.types import InputType
from sima_llm import LLMRouter
from sima_prompts import PromptRegistry

from .awake_loop import AwakeLoop
from .module_runner import ModuleRunner
from .persistence import is_system_paused
from .prayer import setup_prayer_tool
from .senses import SenseCollector
from .settings import Settings
from .telegram import create_telegram_client_from_settings

logger = logging.getLogger(__name__)


class SQSWorker:
    """
    Worker that consumes SQS messages and routes them to the awake loop.

    Supports multiple event types:
    - telegram_update: User message from Telegram webhook
    - minute_tick: Periodic time event (every minute)
    - autonomous_tick: Scheduled autonomous thinking trigger
    """

    def __init__(
        self,
        settings: Settings | None = None,
        awake_loop: AwakeLoop | None = None,
    ):
        """
        Initialize the SQS worker.

        Args:
            settings: Configuration settings.
            awake_loop: Awake loop instance for processing.
        """
        self.settings = settings or Settings()

        # Create telegram client
        self.telegram_client = None
        if self.settings.telegram_bot_token:
            self.telegram_client = create_telegram_client_from_settings(self.settings)

            # Initialize prayer tool for direct communication to Tal
            setup_prayer_tool(
                bot_token=self.settings.telegram_bot_token,
                tal_chat_id=self.settings.telegram_tal_chat_id,
            )

        # Create LLM router and module runner
        self.llm_router = LLMRouter(
            primary_provider=self.settings.llm_primary_provider,
            primary_model=self.settings.llm_primary_model,
            fast_provider=self.settings.llm_fast_provider,
            fast_model=self.settings.llm_fast_model,
            api_keys={"openai": self.settings.openai_api_key} if self.settings.openai_api_key else None,
        )
        self.module_runner = ModuleRunner(
            llm_router=self.llm_router,
            prompt_registry=PromptRegistry(),
        )

        # Create sense collector for interoceptive and environmental awareness
        self.sense_collector = SenseCollector(
            weather_enabled=self.settings.weather_enabled,
            weather_latitude=self.settings.weather_latitude,
            weather_longitude=self.settings.weather_longitude,
            weather_location_name=self.settings.weather_location_name,
            weather_cache_minutes=self.settings.weather_cache_minutes,
            llm_model=self.settings.llm_primary_model,
        )

        # Create awake loop with all components
        self.awake_loop = awake_loop or AwakeLoop(
            settings=self.settings,
            module_runner=self.module_runner,
            telegram_client=self.telegram_client,
            sense_collector=self.sense_collector,
        )

        # Create boto3 session with profile if specified
        session_kwargs = {"region_name": self.settings.aws_region}
        if self.settings.aws_profile:
            session_kwargs["profile_name"] = self.settings.aws_profile
        session = boto3.Session(**session_kwargs)

        # Create SQS client (with optional LocalStack endpoint)
        client_kwargs = {}
        if self.settings.sqs_endpoint_url:
            client_kwargs["endpoint_url"] = self.settings.sqs_endpoint_url
        self.sqs = session.client("sqs", **client_kwargs)
        self.queue_url = self.settings.sqs_queue_url

        # Minute tick configuration
        self.minute_tick_enabled = self.settings.minute_tick_enabled
        self.timezone = ZoneInfo(self.settings.timezone)

    def run(self) -> None:
        """
        Run the worker loop, consuming messages from SQS.

        This is a blocking call that runs indefinitely.
        """
        logger.info(
            f"Starting SQS worker, queue={self.queue_url}, "
            f"minute_tick_enabled={self.minute_tick_enabled}"
        )

        while True:
            try:
                self._poll_and_process()
            except KeyboardInterrupt:
                logger.info("Worker interrupted, shutting down")
                break
            except Exception as e:
                logger.exception(f"Error in worker loop: {e}")

    def _poll_and_process(self) -> None:
        """Poll SQS for messages and process them."""
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            MessageAttributeNames=["All"],
        )

        messages = response.get("Messages", [])
        if not messages:
            return

        for msg in messages:
            try:
                self._process_message(msg)
            except Exception as e:
                logger.exception(f"Error processing message: {e}")
            finally:
                # Delete message from queue
                self.sqs.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=msg["ReceiptHandle"],
                )

    def _process_message(self, sqs_message: dict[str, Any]) -> None:
        """
        Process a single SQS message.

        Routes to appropriate handler based on event_type.
        Respects system paused state - skips processing when paused.
        """
        # Check if system is paused
        if asyncio.run(is_system_paused()):
            logger.info("System is paused, skipping message processing")
            return

        body = json.loads(sqs_message.get("Body", "{}"))
        event_type = body.get("event_type", "telegram_update")

        logger.info(f"Processing message, event_type={event_type}")

        if event_type == "minute_tick":
            if not self.minute_tick_enabled:
                logger.debug("Minute tick disabled, skipping")
                return
            self._handle_minute_tick(body)

        elif event_type == "autonomous_tick":
            self._handle_autonomous_tick(body)

        elif event_type == "telegram_update":
            self._handle_telegram_update(body)

        else:
            logger.warning(f"Unknown event_type: {event_type}")

    def _handle_minute_tick(self, body: dict[str, Any]) -> None:
        """
        Handle a minute tick event.

        Constructs tick metadata and passes to awake loop.
        """
        now = datetime.now(self.timezone)

        tick_metadata = {
            "input_type": "minute_tick",
            "tick_timestamp": now.isoformat(),
            "tick_hour": now.hour,
            "tick_minute": now.minute,
            "tick_day_of_week": now.strftime("%A"),
            "tick_unix": int(now.timestamp()),
        }

        logger.info(
            f"Handling minute tick: {now.strftime('%Y-%m-%d %H:%M')} "
            f"({tick_metadata['tick_day_of_week']})"
        )

        self.awake_loop.run_tick(
            input_type=InputType.MINUTE_TICK,
            tick_metadata=tick_metadata,
        )

    def _handle_autonomous_tick(self, body: dict[str, Any]) -> None:
        """
        Handle an autonomous tick event.

        Similar to minute tick but less frequent, for deeper thinking.
        """
        now = datetime.now(self.timezone)

        tick_metadata = {
            "input_type": "autonomous_tick",
            "tick_timestamp": now.isoformat(),
            "tick_hour": now.hour,
            "tick_minute": now.minute,
            "tick_day_of_week": now.strftime("%A"),
        }

        logger.info(f"Handling autonomous tick: {now.isoformat()}")

        self.awake_loop.run_tick(
            input_type=InputType.AUTONOMOUS_TICK,
            tick_metadata=tick_metadata,
        )

    def _handle_telegram_update(self, body: dict[str, Any]) -> None:
        """
        Handle a Telegram webhook update.

        Extracts message text and passes to awake loop.
        """
        update = body.get("update", body)

        # Extract message from update
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        from_user = message.get("from", {})

        if not text:
            logger.debug("No text in Telegram update, skipping")
            return

        logger.info(f"Handling Telegram message from chat {chat_id}")

        self.awake_loop.run_message(
            message_text=text,
            chat_id=chat_id,
            message_id=message_id,
            from_user=from_user,
        )


def main() -> None:
    """Entry point for the worker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    settings = Settings()
    worker = SQSWorker(settings=settings)
    worker.run()


if __name__ == "__main__":
    main()
