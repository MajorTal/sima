"""
SIMA Ingest API - Telegram webhook receiver.

Receives Telegram webhook updates and enqueues them to SQS
for processing by the orchestrator.
"""

from .main import app

__all__ = ["app"]
