"""
Event definitions for SIMA's event-sourced architecture.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .types import Stream, Actor, EventType
from .ids import generate_id
from .time import utc_now


class EventCreate(BaseModel):
    """Data for creating a new event."""

    trace_id: UUID
    actor: Actor
    stream: Stream
    event_type: EventType
    content_text: str | None = None
    content_json: dict[str, Any] | None = None
    model_provider: str | None = None
    model_id: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    cost_usd: float | None = None
    parent_event_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)


class Event(BaseModel):
    """A persisted event in the system."""

    event_id: UUID = Field(default_factory=generate_id)
    trace_id: UUID
    ts: datetime = Field(default_factory=utc_now)
    actor: Actor
    stream: Stream
    event_type: EventType
    content_text: str | None = None
    content_json: dict[str, Any] | None = None
    model_provider: str | None = None
    model_id: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    cost_usd: float | None = None
    parent_event_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True

    @classmethod
    def from_create(cls, create: EventCreate) -> "Event":
        """Create an Event from EventCreate data."""
        return cls(**create.model_dump())
