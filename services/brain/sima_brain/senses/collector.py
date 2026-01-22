"""
Sense Collector - Orchestrates collection of all sensory data.

Collects both fast senses (every tick) and slow senses (cached).
Returns a unified sensory payload for perception.
"""

import logging
from typing import Any

from .heartbeat import HeartbeatSense
from .breathing import BreathingSense
from .thought_burden import ThoughtBurdenSense
from .tiredness import TirednessSense
from .weather import WeatherSense

logger = logging.getLogger(__name__)


class SenseCollector:
    """
    Orchestrates collection of all sensory data for The Brain.

    Manages both fast senses (collected every tick) and slow senses
    (cached and refreshed on their own schedule).

    Fast Senses:
    - Heartbeat Rate (CPU %)
    - Breathing Rate (Memory %)
    - Thought Burden (Token %)
    - Tiredness (Hours since sleep)

    Slow Senses:
    - Weather (cached, refreshed every 15 minutes, no API key needed)
    """

    def __init__(
        self,
        weather_latitude: float = 52.3676,  # Amsterdam
        weather_longitude: float = 4.9041,
        weather_location_name: str = "Amsterdam, NL",
        weather_cache_minutes: int = 15,
        weather_enabled: bool = True,
        llm_model: str = "gpt-4o",
        llm_context_window: int | None = None,
    ):
        """
        Initialize the sense collector with all senses.

        Args:
            weather_latitude: Latitude for weather sense.
            weather_longitude: Longitude for weather sense.
            weather_location_name: Human-readable location name.
            weather_cache_minutes: Cache duration for weather.
            weather_enabled: Whether to enable weather sense.
            llm_model: Primary LLM model name (for thought burden calculation).
            llm_context_window: Override for model context window size.
        """
        # Fast senses
        self.heartbeat = HeartbeatSense()
        self.breathing = BreathingSense()
        self.thought_burden = ThoughtBurdenSense(
            model_name=llm_model,
            context_window=llm_context_window,
        )
        self.tiredness = TirednessSense()

        # Slow senses (Open-Meteo is free, no API key needed)
        self.weather_enabled = weather_enabled
        self.weather = WeatherSense(
            latitude=weather_latitude,
            longitude=weather_longitude,
            location_name=weather_location_name,
            cache_minutes=weather_cache_minutes,
        ) if weather_enabled else None

    async def collect(
        self,
        memories: list[dict[str, Any]] | None = None,
        additional_context_tokens: int = 0,
    ) -> dict[str, Any]:
        """
        Collect all sensory data.

        Args:
            memories: List of memories loaded into context (for thought burden).
            additional_context_tokens: Extra tokens from prompts, etc.

        Returns:
            Complete sensory payload with all sense readings.
        """
        logger.debug("Collecting sensory data...")

        # Collect fast senses (always collected)
        heartbeat_data = await self.heartbeat.collect()
        breathing_data = await self.breathing.collect()
        thought_burden_data = await self.thought_burden.collect(
            memories=memories,
            additional_context_tokens=additional_context_tokens,
        )
        tiredness_data = await self.tiredness.collect()

        # Collect slow senses (may return cached data)
        weather_data = None
        if self.weather:
            weather_data = await self.weather.collect()

        payload = {
            "heartbeat_rate": heartbeat_data,
            "breathing_rate": breathing_data,
            "thought_burden": thought_burden_data,
            "tiredness": tiredness_data,
        }

        # Weather is optional - only include if available
        if weather_data:
            payload["weather"] = weather_data

        logger.debug(
            f"Sensory collection complete: "
            f"heartbeat={heartbeat_data['value']}%, "
            f"breathing={breathing_data['value']}%, "
            f"thought_burden={thought_burden_data['value']}%, "
            f"tiredness={tiredness_data['value']}h"
        )

        return payload

    async def collect_fast_only(
        self,
        memories: list[dict[str, Any]] | None = None,
        additional_context_tokens: int = 0,
    ) -> dict[str, Any]:
        """
        Collect only fast senses (skip slow senses like weather).

        Useful for performance-critical paths where weather data
        isn't needed or is known to be cached.

        Args:
            memories: List of memories loaded into context.
            additional_context_tokens: Extra tokens from prompts, etc.

        Returns:
            Sensory payload with fast senses only.
        """
        heartbeat_data = await self.heartbeat.collect()
        breathing_data = await self.breathing.collect()
        thought_burden_data = await self.thought_burden.collect(
            memories=memories,
            additional_context_tokens=additional_context_tokens,
        )
        tiredness_data = await self.tiredness.collect()

        return {
            "heartbeat_rate": heartbeat_data,
            "breathing_rate": breathing_data,
            "thought_burden": thought_burden_data,
            "tiredness": tiredness_data,
        }

    def get_summary(self) -> dict[str, Any]:
        """
        Get a summary of the most recent sense readings.

        Returns last collected values without making new measurements.
        """
        return {
            "heartbeat_rate": self.heartbeat.last_reading,
            "breathing_rate": self.breathing.last_reading,
            "thought_burden": self.thought_burden.last_reading,
            "tiredness": self.tiredness.last_reading,
            "weather_cached": self.weather.cached_data is not None if self.weather else False,
        }
