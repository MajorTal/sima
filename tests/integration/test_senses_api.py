"""
Integration tests for external sense APIs.

Tests weather and fear index data sources to ensure they work consistently.
"""

import asyncio
import httpx
import pytest
from datetime import datetime


# Tel Aviv coordinates
TEL_AVIV_LAT = 32.0853
TEL_AVIV_LON = 34.7818


class TestWeatherAPI:
    """Test Open-Meteo weather API (free, no key required)."""

    @pytest.mark.asyncio
    async def test_open_meteo_current_weather(self):
        """Test fetching current weather from Open-Meteo."""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": TEL_AVIV_LAT,
            "longitude": TEL_AVIV_LON,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,is_day",
            "timezone": "Asia/Jerusalem",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)

        assert response.status_code == 200, f"Weather API failed: {response.text}"

        data = response.json()
        assert "current" in data, "Missing 'current' in response"

        current = data["current"]
        assert "temperature_2m" in current, "Missing temperature"
        assert "weather_code" in current, "Missing weather code"

        # Validate data makes sense
        temp = current["temperature_2m"]
        assert -50 < temp < 60, f"Temperature out of range: {temp}"

        print(f"\n✓ Weather API working:")
        print(f"  Temperature: {temp}°C")
        print(f"  Humidity: {current.get('relative_humidity_2m')}%")
        print(f"  Wind: {current.get('wind_speed_10m')} km/h")
        print(f"  Is Day: {current.get('is_day')}")
        print(f"  Weather Code: {current.get('weather_code')}")

        return data


class TestFearIndexAPI:
    """Test fear/volatility index APIs."""

    @pytest.mark.asyncio
    async def test_yahoo_finance_vix(self):
        """Test fetching VIX from Yahoo Finance."""
        # Yahoo Finance API for ^VIX
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX"
        params = {
            "interval": "1d",
            "range": "1d",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)

        assert response.status_code == 200, f"VIX API failed: {response.text}"

        data = response.json()
        chart = data.get("chart", {}).get("result", [{}])[0]
        meta = chart.get("meta", {})

        # Get current price (regularMarketPrice)
        vix_value = meta.get("regularMarketPrice")
        assert vix_value is not None, "Missing VIX value"
        assert 0 < vix_value < 100, f"VIX out of expected range: {vix_value}"

        print(f"\n✓ VIX API working:")
        print(f"  VIX Value: {vix_value}")
        print(f"  Previous Close: {meta.get('previousClose')}")

        return vix_value

    @pytest.mark.asyncio
    async def test_cnn_fear_greed_alternative(self):
        """
        Test alternative fear/greed data source.

        Uses the alternative.me crypto fear & greed index as a proxy.
        More reliable than scraping CNN.
        """
        url = "https://api.alternative.me/fng/"
        params = {"limit": 1}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)

        assert response.status_code == 200, f"Fear & Greed API failed: {response.text}"

        data = response.json()
        assert "data" in data, "Missing 'data' in response"
        assert len(data["data"]) > 0, "Empty data array"

        latest = data["data"][0]
        value = int(latest.get("value", 0))
        classification = latest.get("value_classification", "Unknown")

        assert 0 <= value <= 100, f"Fear index out of range: {value}"

        print(f"\n✓ Fear & Greed API working:")
        print(f"  Value: {value}")
        print(f"  Classification: {classification}")
        print(f"  Timestamp: {latest.get('timestamp')}")

        return {"value": value, "classification": classification}


class TestSensesIntegration:
    """Test combined senses fetch."""

    @pytest.mark.asyncio
    async def test_fetch_all_senses(self):
        """Test fetching all senses in parallel."""
        weather_test = TestWeatherAPI()
        fear_test = TestFearIndexAPI()

        results = await asyncio.gather(
            weather_test.test_open_meteo_current_weather(),
            fear_test.test_yahoo_finance_vix(),
            fear_test.test_cnn_fear_greed_alternative(),
            return_exceptions=True,
        )

        weather_data, vix_value, fear_greed = results

        # At least weather and one fear index should work
        assert not isinstance(weather_data, Exception), f"Weather failed: {weather_data}"

        fear_index_working = (
            not isinstance(vix_value, Exception) or
            not isinstance(fear_greed, Exception)
        )
        assert fear_index_working, "Both fear indices failed"

        print("\n" + "="*50)
        print("✓ All senses integration test passed!")
        print("="*50)


# Utility functions for the actual senses module

def interpret_weather_code(code: int) -> str:
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
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return codes.get(code, f"Unknown ({code})")


def interpret_vix(vix: float) -> dict:
    """Interpret VIX value into market sentiment."""
    if vix < 12:
        level = "extreme_low"
        description = "Extreme complacency - markets very calm"
    elif vix < 20:
        level = "low"
        description = "Low fear - normal calm markets"
    elif vix < 25:
        level = "moderate"
        description = "Moderate concern - some uncertainty"
    elif vix < 30:
        level = "elevated"
        description = "Elevated fear - significant uncertainty"
    elif vix < 40:
        level = "high"
        description = "High fear - markets stressed"
    else:
        level = "extreme"
        description = "Extreme fear - panic conditions"

    return {
        "value": round(vix, 2),
        "level": level,
        "description": description,
    }


def interpret_fear_greed(value: int, classification: str) -> dict:
    """Interpret crypto fear & greed index."""
    return {
        "value": value,
        "classification": classification,
        "is_fearful": value < 40,
        "is_greedy": value > 60,
        "is_neutral": 40 <= value <= 60,
    }


if __name__ == "__main__":
    # Run quick manual test
    async def main():
        print("Testing Senses APIs...\n")

        test = TestSensesIntegration()
        await test.test_fetch_all_senses()

    asyncio.run(main())
