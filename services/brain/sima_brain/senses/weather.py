"""
Weather Sense - Environmental awareness of Amsterdam weather.

Provides ambient environmental context:
- Temperature, humidity, wind
- Weather conditions (sunny, cloudy, rainy, etc.)
- Sunrise/sunset times

Sampling: Every 15 minutes (slow sense, cached)
Source: Open-Meteo API (free, no API key required)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Open-Meteo API endpoint (free, no key required)
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Amsterdam coordinates
DEFAULT_LATITUDE = 52.3676
DEFAULT_LONGITUDE = 4.9041

# Default cache duration
DEFAULT_CACHE_MINUTES = 15

# WMO Weather codes to descriptions
WMO_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌧️"),
    53: ("Moderate drizzle", "🌧️"),
    55: ("Dense drizzle", "🌧️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "🌧️"),
    71: ("Slight snow", "🌨️"),
    73: ("Moderate snow", "🌨️"),
    75: ("Heavy snow", "🌨️"),
    77: ("Snow grains", "🌨️"),
    80: ("Slight rain showers", "🌦️"),
    81: ("Moderate rain showers", "🌦️"),
    82: ("Violent rain showers", "🌦️"),
    85: ("Slight snow showers", "🌨️"),
    86: ("Heavy snow showers", "🌨️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with slight hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️"),
}


class WeatherSense:
    """
    Collects weather data from Open-Meteo API.

    This is a "slow sense" that caches results to avoid excessive API calls.
    Weather data provides environmental context for Sima's perception.

    Open-Meteo is free and requires no API key for non-commercial use.
    """

    def __init__(
        self,
        latitude: float = DEFAULT_LATITUDE,
        longitude: float = DEFAULT_LONGITUDE,
        location_name: str = "Amsterdam, NL",
        cache_minutes: int = DEFAULT_CACHE_MINUTES,
    ):
        """
        Initialize the weather sense.

        Args:
            latitude: Location latitude (default: Amsterdam).
            longitude: Location longitude (default: Amsterdam).
            location_name: Human-readable location name.
            cache_minutes: How long to cache weather data.
        """
        self.latitude = latitude
        self.longitude = longitude
        self.location_name = location_name
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
        Fetch weather data from Open-Meteo API.

        Returns:
            Parsed weather data structure, or None on failure.
        """
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current": [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "weather_code",
                "wind_speed_10m",
                "is_day",
            ],
            "daily": ["sunrise", "sunset"],
            "timezone": "Europe/Amsterdam",
            "forecast_days": 1,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            raw = response.json()

        return self._parse_response(raw)

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Parse Open-Meteo API response into our schema.

        Args:
            raw: Raw API response JSON.

        Returns:
            Structured weather data.
        """
        current = raw.get("current", {})
        daily = raw.get("daily", {})

        # Get weather description from WMO code
        weather_code = current.get("weather_code", 0)
        description, icon = WMO_CODES.get(weather_code, ("Unknown", "❓"))

        # Parse sunrise/sunset (format: "2026-01-22T08:32")
        sunrise_raw = daily.get("sunrise", [None])[0]
        sunset_raw = daily.get("sunset", [None])[0]

        sunrise_str = None
        sunset_str = None
        if sunrise_raw:
            sunrise_str = sunrise_raw.split("T")[1] if "T" in sunrise_raw else sunrise_raw
        if sunset_raw:
            sunset_str = sunset_raw.split("T")[1] if "T" in sunset_raw else sunset_raw

        return {
            "location": self.location_name,
            "temperature": {
                "current": round(current.get("temperature_2m", 0), 1),
                "feels_like": round(current.get("apparent_temperature", 0), 1),
                "unit": "celsius",
            },
            "conditions": {
                "main": description.split()[0] if description else "Unknown",
                "description": description.lower(),
                "icon": icon,
                "code": weather_code,
            },
            "humidity": current.get("relative_humidity_2m", 0),
            "wind": {
                "speed": round(current.get("wind_speed_10m", 0) / 3.6, 1),  # km/h to m/s
                "unit": "m/s",
            },
            "is_day": current.get("is_day", 1) == 1,
            "sun": {
                "sunrise": sunrise_str,
                "sunset": sunset_str,
            },
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "description": f"Weather conditions in {self.location_name.split(',')[0]}",
        }

    @property
    def cached_data(self) -> dict[str, Any] | None:
        """Return the currently cached weather data."""
        return self._cached_data

    def clear_cache(self) -> None:
        """Clear the weather cache, forcing a refresh on next collect."""
        self._cached_data = None
        self._cache_timestamp = None
