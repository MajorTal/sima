"""
Integration tests for sima_api REST endpoints.

These tests require a running API server at localhost:8001.
"""

import pytest
import httpx


API_BASE_URL = "http://localhost:8001"


@pytest.fixture
def api_client():
    """Create an HTTP client for API calls."""
    return httpx.Client(base_url=API_BASE_URL, timeout=10.0)


def is_api_running() -> bool:
    """Check if the API server is running."""
    try:
        with httpx.Client() as client:
            response = client.get(f"{API_BASE_URL}/health", timeout=2.0)
            return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


@pytest.fixture(autouse=True)
def check_api_running():
    """Skip tests if API is not running."""
    if not is_api_running():
        pytest.skip("API server not running at localhost:8001")


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, api_client: httpx.Client):
        """Test health endpoint returns healthy status."""
        response = api_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self, api_client: httpx.Client):
        """Test root endpoint returns service info."""
        response = api_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "sima-api"
        assert "version" in data


class TestTracesEndpoint:
    """Tests for the traces endpoint."""

    def test_list_traces(self, api_client: httpx.Client):
        """Test listing traces."""
        response = api_client.get("/traces")
        assert response.status_code == 200

        data = response.json()
        assert "traces" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["traces"], list)

    def test_list_traces_with_pagination(self, api_client: httpx.Client):
        """Test trace pagination."""
        response = api_client.get("/traces", params={"limit": 5, "offset": 0})
        assert response.status_code == 200

        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0


class TestEventsEndpoint:
    """Tests for the events endpoint."""

    def test_list_recent_events(self, api_client: httpx.Client):
        """Test listing recent events."""
        response = api_client.get("/events")
        assert response.status_code == 200

        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)


class TestAuthEndpoint:
    """Tests for authentication endpoints."""

    def test_auth_check_no_password(self, api_client: httpx.Client):
        """Test auth check when no password is configured."""
        response = api_client.get("/auth/check")
        assert response.status_code == 200

        data = response.json()
        assert "auth_required" in data
