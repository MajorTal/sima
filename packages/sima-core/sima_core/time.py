"""
Time utilities for SIMA.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def format_timestamp(dt: datetime) -> str:
    """Format a datetime as ISO 8601 string."""
    return dt.isoformat()


def parse_timestamp(s: str) -> datetime:
    """Parse an ISO 8601 timestamp string."""
    return datetime.fromisoformat(s)
