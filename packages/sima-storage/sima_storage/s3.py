"""
S3 helpers for large payload storage.
"""

import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from uuid import UUID

import aioboto3


def get_s3_config() -> dict:
    """Get S3 configuration from environment."""
    config = {
        "bucket": os.getenv("S3_BUCKET", "sima-events-dev"),
        "region": os.getenv("AWS_REGION", "us-east-1"),
    }

    # LocalStack endpoint for local development
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    if endpoint_url:
        config["endpoint_url"] = endpoint_url

    return config


@asynccontextmanager
async def get_s3_client() -> AsyncGenerator[Any, None]:
    """Get an async S3 client."""
    config = get_s3_config()
    session = aioboto3.Session()

    client_kwargs = {"region_name": config["region"]}
    if "endpoint_url" in config:
        client_kwargs["endpoint_url"] = config["endpoint_url"]

    async with session.client("s3", **client_kwargs) as client:
        yield client


def make_event_key(trace_id: UUID, event_id: UUID) -> str:
    """Generate S3 key for an event's large payload."""
    return f"events/{trace_id}/{event_id}.json"


def make_trace_key(trace_id: UUID) -> str:
    """Generate S3 key for trace-level data."""
    return f"traces/{trace_id}/data.json"


async def store_large_payload(
    trace_id: UUID,
    event_id: UUID,
    payload: dict[str, Any],
    size_threshold: int = 100_000,  # 100KB
) -> str | None:
    """
    Store a large payload in S3 if it exceeds the threshold.
    Returns the S3 key if stored, None if payload was small enough.
    """
    payload_str = json.dumps(payload)

    if len(payload_str) < size_threshold:
        return None

    config = get_s3_config()
    key = make_event_key(trace_id, event_id)

    async with get_s3_client() as client:
        await client.put_object(
            Bucket=config["bucket"],
            Key=key,
            Body=payload_str.encode("utf-8"),
            ContentType="application/json",
        )

    return key


async def retrieve_payload(s3_key: str) -> dict[str, Any]:
    """Retrieve a payload from S3."""
    config = get_s3_config()

    async with get_s3_client() as client:
        response = await client.get_object(
            Bucket=config["bucket"],
            Key=s3_key,
        )
        body = await response["Body"].read()
        return json.loads(body.decode("utf-8"))


async def store_trace_export(trace_id: UUID, data: dict[str, Any]) -> str:
    """Store a full trace export in S3."""
    config = get_s3_config()
    key = make_trace_key(trace_id)

    async with get_s3_client() as client:
        await client.put_object(
            Bucket=config["bucket"],
            Key=key,
            Body=json.dumps(data, default=str).encode("utf-8"),
            ContentType="application/json",
        )

    return key


async def generate_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for downloading from S3."""
    config = get_s3_config()

    async with get_s3_client() as client:
        url = await client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": config["bucket"],
                "Key": s3_key,
            },
            ExpiresIn=expires_in,
        )
        return url
