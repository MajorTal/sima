"""
Integration tests for sima_sleep service.

These tests require:
- A running PostgreSQL database
- OpenAI API key (optional, for full LLM tests)
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sima_core.types import Actor, EventType, InputType, Stream
from sima_core.events import EventCreate
from sima_storage.database import get_session, init_db, close_db
from sima_storage.repository import TraceRepository, EventRepository, MemoryRepository

from sima_sleep.settings import Settings
from sima_sleep.memory_tier import MemoryTierManager, MemoryType
from sima_sleep.consolidation import SleepConsolidator


@pytest.fixture
async def setup_db(database_url):
    """Initialize database connection for tests."""
    import os
    os.environ["DATABASE_URL"] = database_url

    await init_db()
    yield
    await close_db()


@pytest.fixture
def sleep_settings():
    """Create test settings for sleep service."""
    return Settings(
        database_url="postgresql+asyncpg://sima:sima_dev@localhost:5432/sima",
        sleep_window_hours=24,
        min_traces_for_sleep=1,
        max_events_per_batch=100,
        telegram_telemetry_enabled=False,  # Disable Telegram in tests
    )


@pytest.mark.asyncio
class TestMemoryTierManager:
    """Tests for MemoryTierManager."""

    async def test_load_genesis(self, setup_db):
        """Test loading genesis.md file."""
        async with get_session() as session:
            manager = MemoryTierManager(session)

            # Should load genesis from docs/genesis.md
            content = manager.load_genesis()

            assert content is not None
            assert "Sima" in content
            assert "Thrive" in content

    async def test_ensure_genesis_in_db(self, setup_db):
        """Test persisting genesis to database."""
        async with get_session() as session:
            manager = MemoryTierManager(session)

            # Ensure genesis is in DB
            genesis = await manager.ensure_genesis_in_db()

            assert genesis is not None
            assert genesis.memory_type == MemoryType.L3_GENESIS
            assert "Sima" in genesis.content

    async def test_get_l3_memories(self, setup_db):
        """Test retrieving L3 memories."""
        async with get_session() as session:
            manager = MemoryTierManager(session)

            # Ensure genesis exists
            await manager.ensure_genesis_in_db()

            # Get L3 memories
            memories = await manager.get_l3_memories()

            # Should have at least genesis
            assert len(memories) >= 1

            # Find genesis
            genesis = next(
                (m for m in memories if m.memory_type == MemoryType.L3_GENESIS),
                None
            )
            assert genesis is not None
            assert genesis.name == "genesis"

    async def test_create_l1_digest(self, setup_db):
        """Test creating an L1 trace digest."""
        trace_id = str(uuid4())

        async with get_session() as session:
            manager = MemoryTierManager(session)

            digest = await manager.create_l1_digest(
                trace_id=trace_id,
                topic="Test conversation",
                digest="A test conversation about Python programming.",
                source_event_ids=[str(uuid4())],
            )

            assert digest is not None
            assert digest.memory_type == MemoryType.L1_TRACE_DIGEST
            assert "Python" in digest.content

    async def test_create_semantic_memory(self, setup_db):
        """Test creating a semantic memory."""
        async with get_session() as session:
            manager = MemoryTierManager(session)

            memory = await manager.create_semantic_memory(
                claim="The user prefers Python over JavaScript.",
                confidence=0.85,
                provenance_event_ids=[str(uuid4())],
                source_trace_ids=[str(uuid4())],
            )

            assert memory is not None
            assert memory.memory_type == MemoryType.SEMANTIC
            assert memory.metadata_json["confidence"] == 0.85

    async def test_format_l3_for_context(self, setup_db):
        """Test formatting L3 memories for context."""
        async with get_session() as session:
            manager = MemoryTierManager(session)

            # Ensure genesis exists
            await manager.ensure_genesis_in_db()

            memories = await manager.get_l3_memories()
            formatted = manager.format_l3_for_context(memories)

            assert "GENESIS" in formatted
            assert "Sima" in formatted


@pytest.mark.asyncio
class TestSleepConsolidator:
    """Tests for SleepConsolidator."""

    async def test_run_no_traces(self, setup_db, sleep_settings):
        """Test running sleep with no traces to consolidate."""
        sleep_settings.min_traces_for_sleep = 100  # Won't have 100 traces

        async with get_session() as session:
            consolidator = SleepConsolidator(settings=sleep_settings)
            result = await consolidator.run(session)

            # Should complete without error
            assert result.error is None
            assert result.traces_processed == 0

    async def test_run_with_traces(self, setup_db, sleep_settings, openai_api_key):
        """Test running sleep with actual traces."""
        if not openai_api_key:
            pytest.skip("OpenAI API key required for this test")

        # First, create a trace with events
        trace_id = uuid4()

        async with get_session() as session:
            # Create trace
            trace_repo = TraceRepository(session)
            await trace_repo.create(
                trace_id=trace_id,
                input_type=InputType.USER_MESSAGE,
                user_message="Hello, how are you?",
            )

            # Complete the trace
            await trace_repo.complete(
                trace_id=trace_id,
                response_message="I'm doing well, thank you!",
                total_tokens=50,
                total_cost_usd=0.001,
            )

            # Create some events
            event_repo = EventRepository(session)
            events = [
                EventCreate(
                    trace_id=trace_id,
                    actor=Actor.PERCEPTION,
                    stream=Stream.SUBCONSCIOUS,
                    event_type=EventType.PERCEPT,
                    content_json={"topic": "greeting", "sentiment": "positive"},
                ),
                EventCreate(
                    trace_id=trace_id,
                    actor=Actor.SPEAKER,
                    stream=Stream.EXTERNAL,
                    event_type=EventType.MESSAGE_OUT,
                    content_json={"message": "I'm doing well, thank you!"},
                ),
            ]
            await event_repo.create_many(events)
            await session.commit()

        # Now run consolidation
        async with get_session() as session:
            consolidator = SleepConsolidator(settings=sleep_settings)
            result = await consolidator.run(session)

            # Should process the trace
            assert result.error is None
            assert result.traces_processed >= 1

    async def test_format_events_blob(self, sleep_settings):
        """Test formatting events as JSONL blob."""
        consolidator = SleepConsolidator(settings=sleep_settings)

        # Create mock events
        from unittest.mock import MagicMock

        event1 = MagicMock()
        event1.event_id = uuid4()
        event1.actor = Actor.PERCEPTION
        event1.event_type = EventType.PERCEPT
        event1.content_text = "Test message"
        event1.content_json = {"topic": "test"}

        event2 = MagicMock()
        event2.event_id = uuid4()
        event2.actor = Actor.SPEAKER
        event2.event_type = EventType.MESSAGE_OUT
        event2.content_text = None
        event2.content_json = {"message": "Hello!"}

        blob = consolidator._format_events_blob([event1, event2])

        # Should be JSONL format
        lines = blob.strip().split("\n")
        assert len(lines) == 2

        # Should contain the key fields
        assert "perception" in blob
        assert "speaker" in blob


@pytest.mark.asyncio
class TestMemoryRepository:
    """Tests for MemoryRepository operations used by sleep."""

    async def test_create_and_list_by_type(self, setup_db):
        """Test creating memories and listing by type."""
        async with get_session() as session:
            repo = MemoryRepository(session)

            # Create a semantic memory
            memory = await repo.create(
                memory_id=uuid4(),
                memory_type=MemoryType.SEMANTIC,
                content="Test claim about something.",
                metadata_json={"confidence": 0.9},
            )

            # List by type
            memories = await repo.list_by_type(MemoryType.SEMANTIC, limit=10)

            assert len(memories) >= 1
            assert any(m.memory_id == memory.memory_id for m in memories)

    async def test_record_access(self, setup_db):
        """Test recording memory access."""
        async with get_session() as session:
            repo = MemoryRepository(session)

            # Create memory
            memory = await repo.create(
                memory_id=uuid4(),
                memory_type=MemoryType.SEMANTIC,
                content="Test memory for access tracking.",
            )

            initial_count = memory.access_count

            # Record access
            await repo.record_access(memory.memory_id)
            await session.flush()

        # Verify in new session
        async with get_session() as session:
            repo = MemoryRepository(session)
            updated = await repo.get(memory.memory_id)

            assert updated is not None
            assert updated.access_count == initial_count + 1
            assert updated.last_accessed_at is not None
