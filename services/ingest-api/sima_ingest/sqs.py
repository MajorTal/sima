"""
SQS client for enqueueing messages.
"""

import json
import logging
from typing import Any

import boto3

from .settings import settings

logger = logging.getLogger(__name__)

_sqs_client = None


def get_sqs_client():
    """Get or create the SQS client."""
    global _sqs_client
    if _sqs_client is None:
        kwargs = {"region_name": settings.aws_region}
        if settings.aws_endpoint_url:
            kwargs["endpoint_url"] = settings.aws_endpoint_url
        _sqs_client = boto3.client("sqs", **kwargs)
    return _sqs_client


def enqueue_message(event_type: str, payload: dict[str, Any]) -> str:
    """
    Enqueue a message to SQS.

    Args:
        event_type: Type of event (telegram_update, minute_tick, etc.)
        payload: Message payload.

    Returns:
        SQS message ID.
    """
    if not settings.sqs_queue_url:
        logger.warning("SQS queue URL not configured, skipping enqueue")
        return ""

    client = get_sqs_client()

    message_body = json.dumps({
        "event_type": event_type,
        **payload,
    })

    response = client.send_message(
        QueueUrl=settings.sqs_queue_url,
        MessageBody=message_body,
        MessageAttributes={
            "event_type": {
                "DataType": "String",
                "StringValue": event_type,
            },
        },
    )

    message_id = response["MessageId"]
    logger.info(f"Enqueued message {message_id}, event_type={event_type}")
    return message_id


def enqueue_telegram_update(update: dict[str, Any]) -> str:
    """Enqueue a Telegram update."""
    return enqueue_message("telegram_update", {"update": update})


def enqueue_minute_tick() -> str:
    """Enqueue a minute tick event."""
    return enqueue_message("minute_tick", {})


def enqueue_autonomous_tick() -> str:
    """Enqueue an autonomous tick event."""
    return enqueue_message("autonomous_tick", {})
