"""
SIMA Senses - External environmental data sources.

Provides sensory input to SIMA beyond Telegram messages:
- Weather: temperature, conditions, humidity, wind
- Fear Index: VIX and crypto fear & greed index
"""

from .senses import (
    SenseData,
    WeatherData,
    FearIndexData,
    fetch_all_senses,
    fetch_weather,
    fetch_fear_index,
)

__all__ = [
    "SenseData",
    "WeatherData",
    "FearIndexData",
    "fetch_all_senses",
    "fetch_weather",
    "fetch_fear_index",
]
