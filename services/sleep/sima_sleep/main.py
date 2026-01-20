"""
SIMA Sleep Service - Main Entry Point.

This service runs as a scheduled job (e.g., EventBridge, cron) to perform
memory consolidation during "sleep" cycles.

Usage:
    # Run once (scheduled job mode)
    uv run python -m sima_sleep.main

    # Run with custom sleep window
    uv run python -m sima_sleep.main --window-hours 12

    # Dry run (no persistence)
    uv run python -m sima_sleep.main --dry-run
"""

import argparse
import asyncio
import logging
import sys

from sima_llm import LLMRouter
from sima_prompts import PromptRegistry
from sima_storage.database import get_session, init_db

from .consolidation import SleepConsolidator
from .settings import Settings
from .telegram import create_sleep_telegram_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def run_sleep_cycle(
    settings: Settings,
    dry_run: bool = False,
) -> int:
    """
    Run a single sleep consolidation cycle.

    Args:
        settings: Service settings.
        dry_run: If True, don't persist changes.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    logger.info("=" * 60)
    logger.info("SIMA Sleep Consolidation Service")
    logger.info("=" * 60)

    # Initialize components
    llm_router = LLMRouter()
    prompt_registry = PromptRegistry()
    telegram = create_sleep_telegram_client(settings)

    consolidator = SleepConsolidator(
        settings=settings,
        llm_router=llm_router,
        prompt_registry=prompt_registry,
    )

    # Initialize database
    await init_db()

    try:
        async with get_session() as session:
            # Post sleep start notification
            if settings.telegram_telemetry_enabled:
                await telegram.post_sleep_start("pending")

            # Run consolidation
            result = await consolidator.run(session)

            if result.error:
                logger.error(f"Sleep consolidation failed: {result.error}")

                # Post error notification
                if settings.telegram_telemetry_enabled:
                    await telegram.post_sleep_error(result.sleep_id, result.error)

                return 1

            # Log results
            logger.info(f"Sleep ID: {result.sleep_id}")
            logger.info(f"Traces processed: {result.traces_processed}")
            logger.info(f"Events processed: {result.events_processed}")
            logger.info(f"Digests created: {result.digests_created}")
            logger.info(f"Memories created: {result.memories_created}")

            if result.open_questions:
                logger.info(f"Open questions: {result.open_questions}")
            if result.goal_updates:
                logger.info(f"Goal updates: {result.goal_updates}")

            # Post Telegram notifications
            if settings.telegram_telemetry_enabled and result.completed_at:
                # Post digest
                await telegram.post_sleep_digest(
                    sleep_id=result.sleep_id,
                    trace_count=result.traces_processed,
                    event_count=result.events_processed,
                    trace_digests=[],  # Would need to pass through from consolidation
                    semantic_updates=[],  # Would need to pass through from consolidation
                    open_questions=result.open_questions,
                    goal_updates=result.goal_updates,
                )

                # Post completion
                duration = (result.completed_at - result.started_at).total_seconds()
                await telegram.post_sleep_end(
                    sleep_id=result.sleep_id,
                    duration_seconds=duration,
                    digests_created=result.digests_created,
                    memories_created=result.memories_created,
                )

            if dry_run:
                logger.info("Dry run - rolling back changes")
                await session.rollback()
            else:
                await session.commit()

            logger.info("Sleep consolidation complete")
            return 0

    except Exception as e:
        logger.exception(f"Unexpected error during sleep: {e}")
        return 1

    finally:
        await telegram.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SIMA Sleep Consolidation Service"
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        help="Sleep window in hours (overrides SLEEP_WINDOW_HOURS)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without persisting changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Load settings
    settings = Settings()

    # Apply CLI overrides
    if args.window_hours:
        settings.sleep_window_hours = args.window_hours

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run
    exit_code = asyncio.run(run_sleep_cycle(settings, dry_run=args.dry_run))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
