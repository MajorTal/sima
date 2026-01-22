"""
Tiredness Sense - Hours since last sleep consolidation.

Maps time since sleep to a tiredness metaphor:
- Recent sleep = well rested
- Long time since sleep = exhausted, should sleep

Sampling: Every tick (fast sense)
Source: Database query for last sleep event timestamp
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sima_storage.database import get_session
from sima_storage.models import EventModel
from sqlalchemy import select, desc

logger = logging.getLogger(__name__)


class TirednessSense:
    """
    Tracks hours since the last sleep consolidation.

    This sense reflects how "tired" Sima is based on time since
    the last memory consolidation cycle.

    Interpretation guide (for Sima, not enforced):
    - 0-8 hours: Well rested
    - 8-16 hours: Normal wakefulness
    - 16-24 hours: Getting tired
    - 24+ hours: Exhausted, should sleep
    """

    def __init__(self):
        self._last_reading: float | None = None
        self._last_sleep_at: datetime | None = None

    async def collect(self) -> dict[str, Any]:
        """
        Calculate hours since last sleep consolidation.

        Returns:
            Tiredness data structure with hours since sleep.
        """
        last_sleep_at = await self._get_last_sleep_time()
        now = datetime.now(timezone.utc)

        if last_sleep_at:
            # Ensure timezone-aware comparison
            if last_sleep_at.tzinfo is None:
                last_sleep_at = last_sleep_at.replace(tzinfo=timezone.utc)

            hours_since = (now - last_sleep_at).total_seconds() / 3600
            hours_since = round(hours_since, 1)
        else:
            # No sleep record found - assume freshly started (well rested)
            hours_since = 0.0
            logger.debug("No sleep record found, assuming freshly started")

        self._last_reading = hours_since
        self._last_sleep_at = last_sleep_at

        return {
            "value": hours_since,
            "unit": "hours_since_sleep",
            "last_sleep_at": last_sleep_at.isoformat() if last_sleep_at else None,
            "description": "Hours elapsed since last sleep consolidation",
        }

    async def _get_last_sleep_time(self) -> datetime | None:
        """
        Query the database for the most recent sleep event.

        Returns:
            Timestamp of last sleep completion, or None if never slept.
        """
        try:
            async with get_session() as session:
                # Look for SLEEP_END events which mark completed consolidation
                result = await session.execute(
                    select(EventModel.ts)
                    .where(EventModel.event_type == "SLEEP_END")
                    .order_by(desc(EventModel.ts))
                    .limit(1)
                )
                row = result.scalar_one_or_none()

                if row:
                    return row

                # Fallback: look for SLEEP_START if no SLEEP_END found
                result = await session.execute(
                    select(EventModel.ts)
                    .where(EventModel.event_type == "SLEEP_START")
                    .order_by(desc(EventModel.ts))
                    .limit(1)
                )
                return result.scalar_one_or_none()

        except Exception as e:
            logger.warning(f"Failed to query sleep time: {e}")
            return None

    @property
    def last_reading(self) -> float | None:
        """Return the last calculated tiredness hours."""
        return self._last_reading

    @property
    def last_sleep_at(self) -> datetime | None:
        """Return the timestamp of the last sleep."""
        return self._last_sleep_at
