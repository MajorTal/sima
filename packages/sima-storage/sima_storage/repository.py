"""
Repository classes for database CRUD operations.
"""

from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from sima_core.events import Event, EventCreate
from sima_core.types import Actor, EventType, InputType, Stream

from .models import EventModel, MemoryModel, TraceModel, SystemStateModel


class TraceRepository:
    """Repository for trace operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        trace_id: UUID,
        input_type: InputType,
        telegram_chat_id: int | None = None,
        telegram_message_id: int | None = None,
        user_message: str | None = None,
    ) -> TraceModel:
        """Create a new trace."""
        trace = TraceModel(
            trace_id=trace_id,
            input_type=input_type,
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
            user_message=user_message,
        )
        self.session.add(trace)
        await self.session.flush()
        return trace

    async def get(self, trace_id: UUID) -> TraceModel | None:
        """Get a trace by ID."""
        result = await self.session.execute(
            select(TraceModel).where(TraceModel.trace_id == trace_id)
        )
        return result.scalar_one_or_none()

    async def complete(
        self,
        trace_id: UUID,
        response_message: str | None = None,
        total_tokens: int = 0,
        total_cost_usd: float = 0.0,
    ) -> None:
        """Mark a trace as completed."""
        await self.session.execute(
            update(TraceModel)
            .where(TraceModel.trace_id == trace_id)
            .values(
                completed_at=func.now(),
                response_message=response_message,
                total_tokens=total_tokens,
                total_cost_usd=total_cost_usd,
            )
        )

    async def list_recent(
        self,
        limit: int = 50,
        offset: int = 0,
        input_type: InputType | None = None,
    ) -> Sequence[TraceModel]:
        """List recent traces."""
        query = select(TraceModel).order_by(TraceModel.started_at.desc())

        if input_type is not None:
            query = query.where(TraceModel.input_type == input_type)

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, input_type: InputType | None = None) -> int:
        """Count traces."""
        query = select(func.count(TraceModel.trace_id))
        if input_type is not None:
            query = query.where(TraceModel.input_type == input_type)
        result = await self.session.execute(query)
        return result.scalar_one()


class EventRepository:
    """Repository for event operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, event_create: EventCreate) -> EventModel:
        """Create a new event from EventCreate."""
        event = Event.from_create(event_create)
        model = EventModel(
            event_id=event.event_id,
            trace_id=event.trace_id,
            ts=event.ts,
            actor=event.actor,
            stream=event.stream,
            event_type=event.event_type,
            content_text=event.content_text,
            content_json=event.content_json,
            model_provider=event.model_provider,
            model_id=event.model_id,
            tokens_in=event.tokens_in,
            tokens_out=event.tokens_out,
            latency_ms=event.latency_ms,
            cost_usd=event.cost_usd,
            parent_event_id=event.parent_event_id,
            tags=event.tags,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def create_many(self, events: list[EventCreate]) -> list[EventModel]:
        """Create multiple events."""
        models = []
        for event_create in events:
            event = Event.from_create(event_create)
            model = EventModel(
                event_id=event.event_id,
                trace_id=event.trace_id,
                ts=event.ts,
                actor=event.actor,
                stream=event.stream,
                event_type=event.event_type,
                content_text=event.content_text,
                content_json=event.content_json,
                model_provider=event.model_provider,
                model_id=event.model_id,
                tokens_in=event.tokens_in,
                tokens_out=event.tokens_out,
                latency_ms=event.latency_ms,
                cost_usd=event.cost_usd,
                parent_event_id=event.parent_event_id,
                tags=event.tags,
            )
            models.append(model)

        self.session.add_all(models)
        await self.session.flush()
        return models

    async def get(self, event_id: UUID) -> EventModel | None:
        """Get an event by ID."""
        result = await self.session.execute(
            select(EventModel).where(EventModel.event_id == event_id)
        )
        return result.scalar_one_or_none()

    async def list_by_trace(
        self,
        trace_id: UUID,
        stream: Stream | None = None,
        actor: Actor | None = None,
        event_type: EventType | None = None,
    ) -> Sequence[EventModel]:
        """List events for a trace."""
        query = (
            select(EventModel)
            .where(EventModel.trace_id == trace_id)
            .order_by(EventModel.ts)
        )

        if stream is not None:
            query = query.where(EventModel.stream == stream)
        if actor is not None:
            query = query.where(EventModel.actor == actor)
        if event_type is not None:
            query = query.where(EventModel.event_type == event_type)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_recent(
        self,
        limit: int = 100,
        offset: int = 0,
        stream: Stream | None = None,
    ) -> Sequence[EventModel]:
        """List recent events."""
        query = select(EventModel).order_by(EventModel.ts.desc())

        if stream is not None:
            query = query.where(EventModel.stream == stream)

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_content(
        self,
        query_text: str,
        limit: int = 20,
    ) -> Sequence[EventModel]:
        """Full-text search on content using ParadeDB BM25."""
        # Use ParadeDB pg_search BM25 search
        query = text("""
            SELECT e.* FROM events e
            WHERE e.event_id IN (
                SELECT event_id FROM events
                WHERE content_text @@@ paradedb.parse(:query)
                ORDER BY paradedb.score(event_id) DESC
                LIMIT :limit
            )
            ORDER BY ts DESC
        """)
        result = await self.session.execute(
            query,
            {"query": query_text, "limit": limit}
        )
        return result.scalars().all()

    async def get_trace_stats(self, trace_id: UUID) -> dict:
        """Get aggregate stats for a trace."""
        result = await self.session.execute(
            select(
                func.count(EventModel.event_id).label("event_count"),
                func.sum(EventModel.tokens_in).label("total_tokens_in"),
                func.sum(EventModel.tokens_out).label("total_tokens_out"),
                func.sum(EventModel.cost_usd).label("total_cost"),
            ).where(EventModel.trace_id == trace_id)
        )
        row = result.one()
        return {
            "event_count": row.event_count or 0,
            "total_tokens_in": row.total_tokens_in or 0,
            "total_tokens_out": row.total_tokens_out or 0,
            "total_cost": row.total_cost or 0.0,
        }

    async def get_latest_by_type(
        self,
        event_type: EventType,
        actor: Actor | None = None,
    ) -> EventModel | None:
        """Get the most recent event of a specific type."""
        query = (
            select(EventModel)
            .where(EventModel.event_type == event_type)
            .order_by(EventModel.ts.desc())
            .limit(1)
        )

        if actor is not None:
            query = query.where(EventModel.actor == actor)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class MemoryRepository:
    """Repository for semantic memory operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        memory_id: UUID,
        memory_type: str,
        content: str,
        metadata_json: dict | None = None,
        source_trace_ids: list[str] | None = None,
    ) -> MemoryModel:
        """Create a new memory entry."""
        memory = MemoryModel(
            memory_id=memory_id,
            memory_type=memory_type,
            content=content,
            metadata_json=metadata_json,
            source_trace_ids=source_trace_ids or [],
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def get(self, memory_id: UUID) -> MemoryModel | None:
        """Get a memory by ID."""
        result = await self.session.execute(
            select(MemoryModel).where(MemoryModel.memory_id == memory_id)
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        query_text: str,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> Sequence[MemoryModel]:
        """Search memories using BM25."""
        # Use ParadeDB pg_search for BM25 ranking
        base_query = text("""
            SELECT m.* FROM memories m
            WHERE m.memory_id IN (
                SELECT memory_id FROM memories
                WHERE content @@@ paradedb.parse(:query)
                ORDER BY paradedb.score(memory_id) DESC
                LIMIT :limit
            )
        """)
        result = await self.session.execute(
            base_query,
            {"query": query_text, "limit": limit}
        )
        return result.scalars().all()

    async def list_by_type(
        self,
        memory_type: str,
        limit: int = 50,
    ) -> Sequence[MemoryModel]:
        """List memories by type.

        Supports both exact types (e.g., 'l1_trace_digest') and
        level prefixes (e.g., 'L1', 'L2', 'L3') for convenience.
        """
        # Map level shorthand to prefix pattern
        type_lower = memory_type.lower()
        if type_lower in ("l1", "l2", "l3"):
            # Use prefix matching for level shortcuts
            query = (
                select(MemoryModel)
                .where(MemoryModel.memory_type.ilike(f"{type_lower}%"))
                .order_by(MemoryModel.relevance_score.desc())
                .limit(limit)
            )
        else:
            # Exact match for specific types
            query = (
                select(MemoryModel)
                .where(MemoryModel.memory_type == memory_type)
                .order_by(MemoryModel.relevance_score.desc())
                .limit(limit)
            )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def record_access(self, memory_id: UUID) -> None:
        """Record an access to a memory."""
        await self.session.execute(
            update(MemoryModel)
            .where(MemoryModel.memory_id == memory_id)
            .values(
                access_count=MemoryModel.access_count + 1,
                last_accessed_at=func.now(),
            )
        )


class SystemStateRepository:
    """Repository for system state operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> str | None:
        """Get a system state value."""
        result = await self.session.execute(
            select(SystemStateModel.value).where(SystemStateModel.key == key)
        )
        return result.scalar_one_or_none()

    async def set(self, key: str, value: str) -> None:
        """Set a system state value (upsert)."""
        # Check if exists
        existing = await self.session.execute(
            select(SystemStateModel).where(SystemStateModel.key == key)
        )
        model = existing.scalar_one_or_none()

        if model:
            model.value = value
            model.updated_at = datetime.utcnow()
        else:
            model = SystemStateModel(key=key, value=value)
            self.session.add(model)

        await self.session.flush()

    async def is_paused(self) -> bool:
        """Check if the system is paused."""
        value = await self.get("paused")
        return value == "true"

    async def set_paused(self, paused: bool) -> None:
        """Set the system paused state."""
        await self.set("paused", "true" if paused else "false")
