"""
Event persistence layer for the orchestrator.

Handles storing events and traces to the database using sima-storage.
"""

import logging
from typing import Any
from uuid import UUID

from sima_core.events import EventCreate
from sima_core.types import Actor, EventType, InputType, Stream
from sima_storage.database import get_session
from sima_storage.repository import EventRepository, TraceRepository, SystemStateRepository

logger = logging.getLogger(__name__)


class TracePersistence:
    """
    Persistence layer for a single trace.

    Collects events during a cognitive cycle and persists them atomically.
    """

    def __init__(self, trace_id: UUID):
        """
        Initialize persistence for a trace.

        Args:
            trace_id: The trace UUID.
        """
        self.trace_id = trace_id
        self._events: list[EventCreate] = []
        self._total_tokens_in = 0
        self._total_tokens_out = 0
        self._total_cost = 0.0

    def add_event(
        self,
        actor: Actor,
        stream: Stream,
        event_type: EventType,
        content_text: str | None = None,
        content_json: dict[str, Any] | None = None,
        model_provider: str | None = None,
        model_id: str | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        latency_ms: int | None = None,
        cost_usd: float | None = None,
        parent_event_id: UUID | None = None,
        tags: list[str] | None = None,
    ) -> EventCreate:
        """
        Add an event to the trace.

        Args:
            actor: Module that produced the event.
            stream: Target stream.
            event_type: Type of event.
            content_text: Text content.
            content_json: JSON content.
            model_provider: LLM provider used.
            model_id: LLM model used.
            tokens_in: Input tokens.
            tokens_out: Output tokens.
            latency_ms: Latency in milliseconds.
            cost_usd: Cost in USD.
            parent_event_id: Parent event for threading.
            tags: Event tags.

        Returns:
            The created EventCreate object.
        """
        event = EventCreate(
            trace_id=self.trace_id,
            actor=actor,
            stream=stream,
            event_type=event_type,
            content_text=content_text,
            content_json=content_json,
            model_provider=model_provider,
            model_id=model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            parent_event_id=parent_event_id,
            tags=tags or [],
        )
        self._events.append(event)

        # Track totals
        if tokens_in:
            self._total_tokens_in += tokens_in
        if tokens_out:
            self._total_tokens_out += tokens_out
        if cost_usd:
            self._total_cost += cost_usd

        return event

    def add_input_event(
        self,
        input_type: InputType,
        content_text: str | None = None,
        content_json: dict[str, Any] | None = None,
    ) -> EventCreate:
        """Add an input event (MESSAGE_IN or TICK)."""
        event_type = EventType.MESSAGE_IN if input_type == InputType.USER_MESSAGE else EventType.TICK
        return self.add_event(
            actor=Actor.TELEGRAM_IN if input_type == InputType.USER_MESSAGE else Actor.SYSTEM,
            stream=Stream.EXTERNAL if input_type == InputType.USER_MESSAGE else Stream.SUBCONSCIOUS,
            event_type=event_type,
            content_text=content_text,
            content_json=content_json,
        )

    def add_module_event(
        self,
        actor: Actor,
        event_type: EventType,
        output: dict[str, Any],
        model_provider: str | None = None,
        model_id: str | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        latency_ms: int | None = None,
        cost_usd: float | None = None,
    ) -> EventCreate:
        """Add a module output event."""
        # Determine stream based on event type
        if event_type == EventType.MESSAGE_OUT:
            stream = Stream.EXTERNAL
        elif event_type in (EventType.WORKSPACE_UPDATE, EventType.MONOLOGUE):
            stream = Stream.CONSCIOUS
        else:
            stream = Stream.SUBCONSCIOUS

        return self.add_event(
            actor=actor,
            stream=stream,
            event_type=event_type,
            content_json=output,
            model_provider=model_provider,
            model_id=model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
        )

    def add_output_event(
        self,
        message: str,
    ) -> EventCreate:
        """Add a MESSAGE_OUT event."""
        return self.add_event(
            actor=Actor.TELEGRAM_OUT,
            stream=Stream.EXTERNAL,
            event_type=EventType.MESSAGE_OUT,
            content_text=message,
        )

    @property
    def events(self) -> list[EventCreate]:
        """Get all events."""
        return self._events

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self._total_tokens_in + self._total_tokens_out

    @property
    def total_cost(self) -> float:
        """Get total cost."""
        return self._total_cost


async def create_trace(
    trace_id: UUID,
    input_type: InputType,
    telegram_chat_id: int | None = None,
    telegram_message_id: int | None = None,
    user_message: str | None = None,
) -> None:
    """
    Create a new trace record.

    Args:
        trace_id: Trace UUID.
        input_type: Type of input that triggered the trace.
        telegram_chat_id: Telegram chat ID (for user messages).
        telegram_message_id: Telegram message ID (for user messages).
        user_message: User's message text.
    """
    async with get_session() as session:
        repo = TraceRepository(session)
        await repo.create(
            trace_id=trace_id,
            input_type=input_type,
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=telegram_message_id,
            user_message=user_message,
        )


async def complete_trace(
    trace_id: UUID,
    response_message: str | None = None,
    total_tokens: int = 0,
    total_cost_usd: float = 0.0,
) -> None:
    """
    Mark a trace as completed.

    Args:
        trace_id: Trace UUID.
        response_message: Response sent to user.
        total_tokens: Total tokens used.
        total_cost_usd: Total cost.
    """
    async with get_session() as session:
        repo = TraceRepository(session)
        await repo.complete(
            trace_id=trace_id,
            response_message=response_message,
            total_tokens=total_tokens,
            total_cost_usd=total_cost_usd,
        )


async def persist_events(events: list[EventCreate]) -> None:
    """
    Persist a batch of events to the database.

    Args:
        events: List of events to persist.
    """
    if not events:
        return

    async with get_session() as session:
        repo = EventRepository(session)
        await repo.create_many(events)

    logger.info(f"Persisted {len(events)} events")


async def persist_trace(persistence: TracePersistence, response_message: str | None = None) -> None:
    """
    Persist all events for a trace and mark it complete.

    Args:
        persistence: TracePersistence instance with collected events.
        response_message: Response message sent to user.
    """
    # Persist events
    await persist_events(persistence.events)

    # Complete trace
    await complete_trace(
        trace_id=persistence.trace_id,
        response_message=response_message,
        total_tokens=persistence.total_tokens,
        total_cost_usd=persistence.total_cost,
    )


async def is_system_paused() -> bool:
    """Check if the system is paused."""
    async with get_session() as session:
        repo = SystemStateRepository(session)
        return await repo.is_paused()


async def set_system_paused(paused: bool) -> None:
    """Set the system paused state."""
    async with get_session() as session:
        repo = SystemStateRepository(session)
        await repo.set_paused(paused)
