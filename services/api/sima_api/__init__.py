"""
SIMA API - Backend for web frontend.

Provides REST API and WebSocket endpoints for:
- Trace listing and detail views
- Event queries and streaming
- Indicator metrics
- Admin controls (pause/resume)
"""

from .main import app

__all__ = ["app"]
