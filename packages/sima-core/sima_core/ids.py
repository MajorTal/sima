"""
ID generation utilities for SIMA.
"""

from uuid import UUID, uuid4


def generate_id() -> UUID:
    """Generate a new unique ID."""
    return uuid4()


def generate_trace_id() -> UUID:
    """Generate a new trace ID."""
    return uuid4()
