"""
SQLAlchemy models for SIMA's event-sourced architecture.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


from sima_core.types import Stream, Actor, EventType, InputType


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class TraceModel(Base):
    """A trace represents a single cognitive cycle triggered by an input."""

    __tablename__ = "traces"

    trace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )
    input_type: Mapped[str] = mapped_column(
        SQLEnum(
            InputType,
            name="input_type_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    telegram_chat_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    telegram_message_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    user_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    response_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    total_cost_usd: Mapped[float] = mapped_column(
        Float,
        default=0.0,
    )

    # Relationships
    events: Mapped[list["EventModel"]] = relationship(
        "EventModel",
        back_populates="trace",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_traces_started_at", "started_at"),
        Index("ix_traces_input_type", "input_type"),
    )


class EventModel(Base):
    """An event in the system - the core unit of storage."""

    __tablename__ = "events"

    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )
    trace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("traces.trace_id", ondelete="CASCADE"),
        nullable=False,
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    actor: Mapped[str] = mapped_column(
        SQLEnum(
            Actor,
            name="actor_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    stream: Mapped[str] = mapped_column(
        SQLEnum(
            Stream,
            name="stream_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        SQLEnum(
            EventType,
            name="event_type_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    content_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    content_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    model_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    model_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    tokens_in: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    tokens_out: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    cost_usd: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    parent_event_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("events.event_id", ondelete="SET NULL"),
        nullable=True,
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
    )
    s3_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Relationships
    trace: Mapped["TraceModel"] = relationship(
        "TraceModel",
        back_populates="events",
    )

    __table_args__ = (
        Index("ix_events_trace_id", "trace_id"),
        Index("ix_events_ts", "ts"),
        Index("ix_events_actor", "actor"),
        Index("ix_events_stream", "stream"),
        Index("ix_events_event_type", "event_type"),
        Index("ix_events_content_json", "content_json", postgresql_using="gin"),
    )


class MemoryModel(Base):
    """Semantic memory entries consolidated from traces."""

    __tablename__ = "memories"

    memory_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
    )
    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    source_trace_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
    )
    relevance_score: Mapped[float] = mapped_column(
        Float,
        default=1.0,
    )
    access_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_memories_memory_type", "memory_type"),
        Index("ix_memories_created_at", "created_at"),
        Index("ix_memories_relevance_score", "relevance_score"),
    )


class SystemStateModel(Base):
    """System state for pause/resume functionality."""

    __tablename__ = "system_state"

    key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )
    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
