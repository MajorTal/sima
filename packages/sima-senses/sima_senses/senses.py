"""
Senses module for SIMA.

Fetches external environmental data to enrich Sima's perception:
- Weather from Open-Meteo API (free, no key required)
- Fear index from VIX and crypto fear & greed index
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default location: Tel Aviv
DEFAULT_LAT = 32.0853
DEFAULT_LON = 34.7818
DEFAULT_TIMEZONE = "Asia/Jerusalem"

# API timeout
API_TIMEOUT = 10.0


@dataclass
class WeatherData:
    """Weather sense data."""

    temperature_c: float
    humidity_percent: int
    wind_speed_kmh: float
    weather_code: int
    weather_description: str
    is_day: bool
    fetched_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "temperature_c": self.temperature_c,
            "humidity_percent": self.humidity_percent,
            "wind_speed_kmh": self.wind_speed_kmh,
            "weather_code": self.weather_code,
            "weather_description": self.weather_description,
            "is_day": self.is_day,
            "fetched_at": self.fetched_at,
        }


@dataclass
class FearIndexData:
    """Fear index sense data."""

    vix_value: float | None = None
    vix_level: str | None = None
    vix_description: str | None = None
    crypto_fear_value: int | None = None
    crypto_fear_classification: str | None = None
    combined_fear_level: str = "unknown"
    fetched_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "vix_value": self.vix_value,
            "vix_level": self.vix_level,
            "vix_description": self.vix_description,
            "crypto_fear_value": self.crypto_fear_value,
            "crypto_fear_classification": self.crypto_fear_classification,
            "combined_fear_level": self.combined_fear_level,
            "fetched_at": self.fetched_at,
        }


@dataclass
class SenseData:
    """Combined sense data from all sources."""

    weather: WeatherData | None = None
    fear_index: FearIndexData | None = None
    errors: list[str] = field(default_factory=list)
    fetched_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "weather": self.weather.to_dict() if self.weather else None,
            "fear_index": self.fear_index.to_dict() if self.fear_index else None,
            "errors": self.errors,
            "fetched_at": self.fetched_at,
        }

    def has_data(self) -> bool:
        """Check if any sense data was fetched successfully."""
        return self.weather is not None or self.fear_index is not None


def _interpret_weather_code(code: int) -> str:
    """Convert WMO weather code to human-readable description."""
    codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return codes.get(code, f"Unknown weather ({code})")


def _interpret_vix(vix: float) -> tuple[str, str]:
    """Interpret VIX value into market sentiment level and description."""
    if vix < 12:
        return "extreme_calm", "Extreme complacency - markets unusually calm"
    elif vix < 20:
        return "calm", "Low fear - normal calm markets"
    elif vix < 25:
        return "moderate", "Moderate concern - some uncertainty"
    elif vix < 30:
        return "elevated", "Elevated fear - significant uncertainty"
    elif vix < 40:
        return "high", "High fear - markets stressed"
    else:
        return "extreme_fear", "Extreme fear - panic conditions"


def _compute_combined_fear_level(
    vix_value: float | None,
    crypto_fear_value: int | None,
) -> str:
    """Compute a combined fear level from available indices."""
    scores = []

    if vix_value is not None:
        # Normalize VIX to 0-100 scale (VIX rarely goes above 80)
        vix_normalized = min(vix_value * 1.25, 100)
        scores.append(vix_normalized)

    if crypto_fear_value is not None:
        # Crypto fear index is inverted (0 = extreme fear, 100 = extreme greed)
        # We want higher = more fear, so invert it
        crypto_inverted = 100 - crypto_fear_value
        scores.append(crypto_inverted)

    if not scores:
        return "unknown"

    avg_score = sum(scores) / len(scores)

    if avg_score < 25:
        return "calm"
    elif avg_score < 45:
        return "moderate"
    elif avg_score < 65:
        return "elevated"
    elif avg_score < 80:
        return "high"
    else:
        return "extreme_fear"


async def fetch_weather(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    timezone: str = DEFAULT_TIMEZONE,
) -> WeatherData | None:
    """
    Fetch current weather from Open-Meteo API.

    Args:
        lat: Latitude (default: Tel Aviv)
        lon: Longitude (default: Tel Aviv)
        timezone: Timezone string (default: Asia/Jerusalem)

    Returns:
        WeatherData if successful, None on error
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,is_day",
        "timezone": timezone,
    }

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(url, params=params)

        if response.status_code != 200:
            logger.warning(f"Weather API returned status {response.status_code}")
            return None

        data = response.json()
        current = data.get("current", {})

        weather_code = current.get("weather_code", 0)

        return WeatherData(
            temperature_c=current.get("temperature_2m", 0),
            humidity_percent=int(current.get("relative_humidity_2m", 0)),
            wind_speed_kmh=current.get("wind_speed_10m", 0),
            weather_code=weather_code,
            weather_description=_interpret_weather_code(weather_code),
            is_day=bool(current.get("is_day", 1)),
            fetched_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return None


async def _fetch_vix() -> tuple[float | None, str | None, str | None]:
    """Fetch VIX from Yahoo Finance."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX"
    params = {"interval": "1d", "range": "1d"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(url, params=params, headers=headers)

        if response.status_code != 200:
            logger.warning(f"VIX API returned status {response.status_code}")
            return None, None, None

        data = response.json()
        chart = data.get("chart", {}).get("result", [{}])[0]
        meta = chart.get("meta", {})

        vix_value = meta.get("regularMarketPrice")
        if vix_value is None:
            return None, None, None

        level, description = _interpret_vix(vix_value)
        return round(vix_value, 2), level, description

    except Exception as e:
        logger.error(f"Error fetching VIX: {e}")
        return None, None, None


async def _fetch_crypto_fear() -> tuple[int | None, str | None]:
    """Fetch crypto fear & greed index from alternative.me."""
    url = "https://api.alternative.me/fng/"
    params = {"limit": 1}

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(url, params=params)

        if response.status_code != 200:
            logger.warning(f"Crypto fear API returned status {response.status_code}")
            return None, None

        data = response.json()
        if "data" not in data or not data["data"]:
            return None, None

        latest = data["data"][0]
        value = int(latest.get("value", 0))
        classification = latest.get("value_classification", "Unknown")

        return value, classification

    except Exception as e:
        logger.error(f"Error fetching crypto fear index: {e}")
        return None, None


async def fetch_fear_index() -> FearIndexData | None:
    """
    Fetch fear indices from multiple sources.

    Fetches both VIX and crypto fear & greed index in parallel,
    combines them into a unified fear assessment.

    Returns:
        FearIndexData if at least one source succeeded, None if all failed
    """
    try:
        # Fetch both in parallel
        vix_result, crypto_result = await asyncio.gather(
            _fetch_vix(),
            _fetch_crypto_fear(),
            return_exceptions=True,
        )

        # Handle VIX result
        vix_value, vix_level, vix_description = (None, None, None)
        if not isinstance(vix_result, Exception):
            vix_value, vix_level, vix_description = vix_result

        # Handle crypto fear result
        crypto_value, crypto_classification = (None, None)
        if not isinstance(crypto_result, Exception):
            crypto_value, crypto_classification = crypto_result

        # If both failed, return None
        if vix_value is None and crypto_value is None:
            return None

        # Compute combined fear level
        combined = _compute_combined_fear_level(vix_value, crypto_value)

        return FearIndexData(
            vix_value=vix_value,
            vix_level=vix_level,
            vix_description=vix_description,
            crypto_fear_value=crypto_value,
            crypto_fear_classification=crypto_classification,
            combined_fear_level=combined,
            fetched_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error fetching fear index: {e}")
        return None


async def fetch_all_senses(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    timezone: str = DEFAULT_TIMEZONE,
) -> SenseData:
    """
    Fetch all sense data in parallel.

    Args:
        lat: Latitude for weather (default: Tel Aviv)
        lon: Longitude for weather (default: Tel Aviv)
        timezone: Timezone string (default: Asia/Jerusalem)

    Returns:
        SenseData with all available sense data and any errors
    """
    errors: list[str] = []

    # Fetch all senses in parallel
    results = await asyncio.gather(
        fetch_weather(lat, lon, timezone),
        fetch_fear_index(),
        return_exceptions=True,
    )

    weather_result, fear_result = results

    # Process weather result
    weather: WeatherData | None = None
    if isinstance(weather_result, Exception):
        errors.append(f"Weather fetch failed: {weather_result}")
    else:
        weather = weather_result

    # Process fear index result
    fear_index: FearIndexData | None = None
    if isinstance(fear_result, Exception):
        errors.append(f"Fear index fetch failed: {fear_result}")
    else:
        fear_index = fear_result

    return SenseData(
        weather=weather,
        fear_index=fear_index,
        errors=errors,
        fetched_at=datetime.utcnow().isoformat(),
    )
