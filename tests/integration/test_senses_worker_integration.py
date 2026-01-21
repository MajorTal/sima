"""
Integration tests for senses in the orchestrator worker.

Tests that sensory data flows correctly through the tick handling.
"""

import asyncio
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock, patch

from sima_senses import fetch_all_senses, SenseData


class TestSensesWorkerIntegration:
    """Test senses integration in the worker tick handling."""

    @pytest.mark.asyncio
    async def test_fetch_senses_returns_data(self):
        """Verify fetch_all_senses returns valid data."""
        data = await fetch_all_senses()

        assert isinstance(data, SenseData)
        assert data.has_data(), "Should have some sensory data"

        # At least weather should be available
        assert data.weather is not None, "Weather should be fetched"
        assert data.weather.temperature_c is not None
        assert data.weather.weather_description is not None

        print(f"\nWeather: {data.weather.temperature_c}°C, {data.weather.weather_description}")

        # Fear index should also be available
        if data.fear_index:
            print(f"Fear: VIX={data.fear_index.vix_value}, Combined={data.fear_index.combined_fear_level}")

    @pytest.mark.asyncio
    async def test_senses_to_dict_format(self):
        """Verify the dict format is correct for tick_metadata."""
        data = await fetch_all_senses()
        dict_data = data.to_dict()

        # Check structure matches what perception prompt expects
        assert "weather" in dict_data
        assert "fear_index" in dict_data
        assert "errors" in dict_data
        assert "fetched_at" in dict_data

        if dict_data["weather"]:
            weather = dict_data["weather"]
            assert "temperature_c" in weather
            assert "humidity_percent" in weather
            assert "wind_speed_kmh" in weather
            assert "weather_code" in weather
            assert "weather_description" in weather
            assert "is_day" in weather

        if dict_data["fear_index"]:
            fear = dict_data["fear_index"]
            assert "combined_fear_level" in fear
            # VIX or crypto should be present
            has_vix = fear.get("vix_value") is not None
            has_crypto = fear.get("crypto_fear_value") is not None
            assert has_vix or has_crypto, "Should have at least one fear index"

    @pytest.mark.asyncio
    async def test_tick_metadata_integration(self):
        """Test that senses can be added to tick_metadata correctly."""
        from zoneinfo import ZoneInfo
        from datetime import datetime

        timezone = ZoneInfo("Asia/Jerusalem")
        now = datetime.now(timezone)

        # Simulate what the worker does
        tick_metadata = {
            "input_type": "minute_tick",
            "tick_timestamp": now.isoformat(),
            "tick_hour": now.hour,
            "tick_minute": now.minute,
            "tick_day_of_week": now.strftime("%A"),
            "tick_unix": int(now.timestamp()),
        }

        # Fetch senses
        sense_data = await fetch_all_senses()
        if sense_data.has_data():
            tick_metadata["senses"] = sense_data.to_dict()

        # Verify structure
        assert "senses" in tick_metadata
        senses = tick_metadata["senses"]
        assert senses["weather"] is not None

        print("\nTick metadata with senses:")
        print(f"  Time: {tick_metadata['tick_hour']:02d}:{tick_metadata['tick_minute']:02d}")
        print(f"  Weather: {senses['weather']['temperature_c']}°C")
        if senses["fear_index"]:
            print(f"  Fear Level: {senses['fear_index']['combined_fear_level']}")


class TestSensesResilience:
    """Test that senses module handles errors gracefully."""

    @pytest.mark.asyncio
    async def test_handles_weather_failure(self):
        """Test graceful handling when weather API fails."""
        with patch("sima_senses.senses.httpx.AsyncClient") as mock_client:
            # Make weather call fail
            mock_instance = MagicMock()
            mock_instance.get = MagicMock(side_effect=Exception("Network error"))
            mock_instance.__aenter__ = MagicMock(return_value=mock_instance)
            mock_instance.__aexit__ = MagicMock(return_value=None)
            mock_client.return_value = mock_instance

            data = await fetch_all_senses()

            # Should still return a SenseData, just with errors
            assert isinstance(data, SenseData)
            # Note: both weather and fear_index will fail since we mocked the client

    @pytest.mark.asyncio
    async def test_partial_data_is_useful(self):
        """Test that partial data (only weather or only fear) is still useful."""
        data = await fetch_all_senses()

        # Even if one fails, we should have something
        # In practice both work, but the structure supports partial data
        dict_data = data.to_dict()

        # Check that None values don't break serialization
        import json
        json_str = json.dumps(dict_data)
        assert json_str is not None


if __name__ == "__main__":
    async def main():
        print("Running senses worker integration tests...\n")

        test = TestSensesWorkerIntegration()
        await test.test_fetch_senses_returns_data()
        await test.test_senses_to_dict_format()
        await test.test_tick_metadata_integration()

        print("\n✓ All tests passed!")

    asyncio.run(main())
