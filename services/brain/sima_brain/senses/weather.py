"""
Weather Sense - Environmental awareness of Amsterdam weather.

Provides ambient environmental context:
- Temperature, humidity, wind
- Weather conditions (sunny, cloudy, rainy, etc.)
- Sunrise/sunset times

Sampling: Every 15 minutes (slow sense, cached)
Source: OpenWeatherMap API
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# OpenWeatherMap API endpoint
OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/2.5/weather"

# Default cache duration
DEFAULT_CACHE_MINUTES = 15


class WeatherSense:
    """
    Collects weather data from OpenWeatherMap API.

    This is a "slow sense" that caches results to avoid excessive API calls.
    Weather data provides environmental context for Sima's perception.

    The weather sense is optional - if no API key is configured, it returns
    None without failing the sense collection.
    """

    def __init__(
        self,
        api_key: str | None = None,
        location: str = "Amsterdam,NL",
        cache_minutes: int = DEFAULT_CACHE_MINUTES,
    ):
        """
        Initialize the weather sense.

        Args:
            api_key: OpenWeatherMap API key.
            location: City and country code (e.g., "Amsterdam,NL").
            cache_minutes: How long to cache weather data.
        """
        self.api_key = api_key
        self.location = location
        self.cache_minutes = cache_minutes

        # Cache state
        self._cached_data: dict[str, Any] | None = None
        self._cache_timestamp: datetime | None = None

    async def collect(self) -> dict[str, Any] | None:
        """
        Collect current weather data, using cache if valid.

        Returns:
            Weather data structure, or None if unavailable.
        """
        if not self.api_key:
            logger.debug("Weather sense disabled (no API key)")
            return None

        # Check cache validity
        if self._is_cache_valid():
            logger.debug("Using cached weather data")
            return self._cached_data

        # Fetch fresh data
        try:
            data = await self._fetch_weather()
            if data:
                self._cached_data = data
                self._cache_timestamp = datetime.now(timezone.utc)
            return data
        except Exception as e:
            logger.warning(f"Failed to fetch weather: {e}")
            # Return stale cache if available
            if self._cached_data:
                logger.debug("Returning stale weather cache after fetch failure")
                return self._cached_data
            return None

    def _is_cache_valid(self) -> bool:
        """Check if the cached weather data is still valid."""
        if self._cached_data is None or self._cache_timestamp is None:
            return False

        age = datetime.now(timezone.utc) - self._cache_timestamp
        return age < timedelta(minutes=self.cache_minutes)

    async def _fetch_weather(self) -> dict[str, Any] | None:
        """
        Fetch weather data from OpenWeatherMap API.

        Returns:
            Parsed weather data structure, or None on failure.
        """
        params = {
            "q": self.location,
            "appid": self.api_key,
            "units": "metric",  # Celsius
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPENWEATHERMAP_URL, params=params)
            response.raise_for_status()
            raw = response.json()

        return self._parse_response(raw)

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Parse OpenWeatherMap API response into our schema.

        Args:
            raw: Raw API response JSON.

        Returns:
            Structured weather data.
        """
        main = raw.get("main", {})
        weather = raw.get("weather", [{}])[0]
        wind = raw.get("wind", {})
        sys = raw.get("sys", {})

        # Convert Unix timestamps to time strings
        sunrise_ts = sys.get("sunrise")
        sunset_ts = sys.get("sunset")

        sunrise_str = None
        sunset_str = None
        if sunrise_ts:
            sunrise_str = datetime.fromtimestamp(sunrise_ts, tz=timezone.utc).strftime("%H:%M")
        if sunset_ts:
            sunset_str = datetime.fromtimestamp(sunset_ts, tz=timezone.utc).strftime("%H:%M")

        return {
            "location": self.location,
            "temperature": {
                "current": round(main.get("temp", 0), 1),
                "feels_like": round(main.get("feels_like", 0), 1),
                "unit": "celsius",
            },
            "conditions": {
                "main": weather.get("main", "Unknown"),
                "description": weather.get("description", "unknown"),
                "icon": weather.get("icon", ""),
            },
            "humidity": main.get("humidity", 0),
            "wind": {
                "speed": round(wind.get("speed", 0), 1),
                "unit": "m/s",
            },
            "sun": {
                "sunrise": sunrise_str,
                "sunset": sunset_str,
            },
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "description": f"Weather conditions in {self.location.split(',')[0]}",
        }

    @property
    def cached_data(self) -> dict[str, Any] | None:
        """Return the currently cached weather data."""
        return self._cached_data

    def clear_cache(self) -> None:
        """Clear the weather cache, forcing a refresh on next collect."""
        self._cached_data = None
        self._cache_timestamp = None
