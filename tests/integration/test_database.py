"""
Integration tests for sima_storage database operations.

These tests require a running PostgreSQL database.
"""

import pytest
from uuid import uuid4

from sima_core.types import Actor, EventType, InputType, Stream
from sima_core.events import EventCreate
from sima_storage.database import get_session, init_db, close_db
from sima_storage.repository import TraceRepository, EventRepository


@pytest.fixture
async def setup_db(database_url):
    """Initialize database connection for tests."""
    import os
    os.environ["DATABASE_URL"] = database_url

    await init_db()
    yield
    await close_db()


@pytest.mark.asyncio
class TestTraceRepository:
    """Tests for TraceRepository."""

    async def test_create_and_get_trace(self, setup_db):
        """Test creating and retrieving a trace."""
        trace_id = uuid4()

        async with get_session() as session:
            repo = TraceRepository(session)

            # Create trace
            trace = await repo.create(
                trace_id=trace_id,
                input_type=InputType.USER_MESSAGE,
                telegram_chat_id=12345,
                telegram_message_id=1,
                user_message="Hello, test!",
            )

            assert trace is not None
            assert trace.trace_id == trace_id
            assert trace.input_type == InputType.USER_MESSAGE

            # Retrieve trace
            retrieved = await repo.get(trace_id)
            assert retrieved is not None
            assert retrieved.trace_id == trace_id
            assert retrieved.user_message == "Hello, test!"

    async def test_complete_trace(self, setup_db):
        """Test completing a trace with response."""
        trace_id = uuid4()

        async with get_session() as session:
            repo = TraceRepository(session)

            # Create trace
            await repo.create(
                trace_id=trace_id,
                input_type=InputType.USER_MESSAGE,
            )

            # Complete trace
            await repo.complete(
                trace_id=trace_id,
                response_message="Hello back!",
                total_tokens=100,
                total_cost_usd=0.001,
            )

        # Verify in new session
        async with get_session() as session:
            repo = TraceRepository(session)
            trace = await repo.get(trace_id)

            assert trace is not None
            assert trace.response_message == "Hello back!"
            assert trace.total_tokens == 100
            assert trace.completed_at is not None

    async def test_list_recent_traces(self, setup_db):
        """Test listing recent traces."""
        async with get_session() as session:
            repo = TraceRepository(session)

            # Create a few traces
            for _ in range(3):
                await repo.create(
                    trace_id=uuid4(),
                    input_type=InputType.USER_MESSAGE,
                )

            # List traces
            traces = await repo.list_recent(limit=10)
            assert len(traces) >= 3

    async def test_count_traces(self, setup_db):
        """Test counting traces."""
        async with get_session() as session:
            repo = TraceRepository(session)
            count = await repo.count()
            assert count >= 0


@pytest.mark.asyncio
class TestEventRepository:
    """Tests for EventRepository."""

    async def test_create_event(self, setup_db):
        """Test creating an event."""
        trace_id = uuid4()

        async with get_session() as session:
            # First create a trace
            trace_repo = TraceRepository(session)
            await trace_repo.create(
                trace_id=trace_id,
                input_type=InputType.USER_MESSAGE,
            )

            # Create event
            event_repo = EventRepository(session)
            event_create = EventCreate(
                trace_id=trace_id,
                actor=Actor.PERCEPTION,
                stream=Stream.SUBCONSCIOUS,
                event_type=EventType.PERCEPT,
                content_json={"test": "data"},
            )

            event = await event_repo.create(event_create)
            assert event is not None
            assert event.trace_id == trace_id
            assert event.actor == Actor.PERCEPTION

    async def test_list_events_by_trace(self, setup_db):
        """Test listing events for a trace."""
        trace_id = uuid4()

        async with get_session() as session:
            # Create trace
            trace_repo = TraceRepository(session)
            await trace_repo.create(
                trace_id=trace_id,
                input_type=InputType.USER_MESSAGE,
            )

            # Create multiple events
            event_repo = EventRepository(session)
            events_to_create = [
                EventCreate(
                    trace_id=trace_id,
                    actor=Actor.PERCEPTION,
                    stream=Stream.SUBCONSCIOUS,
                    event_type=EventType.PERCEPT,
                    content_json={"step": 1},
                ),
                EventCreate(
                    trace_id=trace_id,
                    actor=Actor.WORKSPACE,
                    stream=Stream.CONSCIOUS,
                    event_type=EventType.WORKSPACE_UPDATE,
                    content_json={"step": 2},
                ),
            ]
            await event_repo.create_many(events_to_create)

            # List events
            events = await event_repo.list_by_trace(trace_id)
            assert len(events) == 2

    async def test_filter_events_by_stream(self, setup_db):
        """Test filtering events by stream."""
        trace_id = uuid4()

        async with get_session() as session:
            trace_repo = TraceRepository(session)
            await trace_repo.create(
                trace_id=trace_id,
                input_type=InputType.USER_MESSAGE,
            )

            event_repo = EventRepository(session)
            events_to_create = [
                EventCreate(
                    trace_id=trace_id,
                    actor=Actor.PERCEPTION,
                    stream=Stream.SUBCONSCIOUS,
                    event_type=EventType.PERCEPT,
                    content_json={},
                ),
                EventCreate(
                    trace_id=trace_id,
                    actor=Actor.WORKSPACE,
                    stream=Stream.CONSCIOUS,
                    event_type=EventType.WORKSPACE_UPDATE,
                    content_json={},
                ),
            ]
            await event_repo.create_many(events_to_create)

            # Filter by stream
            conscious_events = await event_repo.list_by_trace(
                trace_id, stream=Stream.CONSCIOUS
            )
            assert len(conscious_events) == 1
            assert conscious_events[0].stream == Stream.CONSCIOUS
