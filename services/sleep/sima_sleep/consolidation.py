"""
Sleep Consolidation Job.

This module implements the sleep consolidation logic:
1. Query traces from the sleep window
2. Fetch events for those traces
3. Run LLM consolidation to produce digests and memories
4. Persist consolidated memories
5. Post telemetry to Telegram
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sima_core.types import Actor, EventType, Stream
from sima_core.events import EventCreate
from sima_llm import LLMRouter
from sima_prompts import PromptRegistry, render_prompt
from sima_storage.models import EventModel, TraceModel
from sima_storage.repository import EventRepository, MemoryRepository, TraceRepository

from .memory_tier import MemoryTierManager, MemoryType
from .settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class SleepResult:
    """Result of a sleep consolidation cycle."""

    sleep_id: str
    started_at: datetime
    completed_at: datetime | None
    traces_processed: int
    events_processed: int
    digests_created: int
    memories_created: int
    open_questions: list[str]
    goal_updates: list[str]
    error: str | None = None


@dataclass
class ConsolidationContext:
    """Context for a sleep consolidation cycle."""

    sleep_id: str
    session: AsyncSession
    settings: Settings
    llm: LLMRouter
    prompts: PromptRegistry
    memory_manager: MemoryTierManager
    trace_repo: TraceRepository
    event_repo: EventRepository
    memory_repo: MemoryRepository
    events_to_persist: list[EventCreate]
    started_at: datetime


class SleepConsolidator:
    """
    Handles the sleep consolidation process.

    During "sleep", Sima:
    - Compacts recent traces into L1 digests
    - Extracts stable semantic memories
    - Identifies open questions and goal updates
    - Updates the memory tier system
    """

    def __init__(
        self,
        settings: Settings,
        llm_router: LLMRouter | None = None,
        prompt_registry: PromptRegistry | None = None,
    ):
        """
        Initialize the sleep consolidator.

        Args:
            settings: Service settings.
            llm_router: LLM router for completions.
            prompt_registry: Prompt registry for loading prompts.
        """
        self.settings = settings
        self.llm = llm_router or LLMRouter()
        self.prompts = prompt_registry or PromptRegistry()

    async def run(self, session: AsyncSession) -> SleepResult:
        """
        Run a sleep consolidation cycle.

        Args:
            session: Database session.

        Returns:
            SleepResult with consolidation outcome.
        """
        sleep_id = str(uuid4())
        started_at = datetime.now(timezone.utc)

        logger.info(f"Starting sleep consolidation cycle {sleep_id}")

        # Initialize context
        ctx = ConsolidationContext(
            sleep_id=sleep_id,
            session=session,
            settings=self.settings,
            llm=self.llm,
            prompts=self.prompts,
            memory_manager=MemoryTierManager(session),
            trace_repo=TraceRepository(session),
            event_repo=EventRepository(session),
            memory_repo=MemoryRepository(session),
            events_to_persist=[],
            started_at=started_at,
        )

        try:
            # Record sleep start
            self._add_event(ctx, EventType.SLEEP_START, {
                "sleep_id": sleep_id,
                "started_at": started_at.isoformat(),
            })

            # Ensure genesis.md is in DB
            await ctx.memory_manager.ensure_genesis_in_db()

            # Get traces from sleep window
            traces = await self._get_traces_for_consolidation(ctx)

            if len(traces) < self.settings.min_traces_for_sleep:
                logger.info(f"Not enough traces for consolidation ({len(traces)} < {self.settings.min_traces_for_sleep})")
                return SleepResult(
                    sleep_id=sleep_id,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    traces_processed=0,
                    events_processed=0,
                    digests_created=0,
                    memories_created=0,
                    open_questions=[],
                    goal_updates=[],
                )

            # Fetch events for traces
            events = await self._fetch_events_for_traces(ctx, traces)
            logger.info(f"Fetched {len(events)} events from {len(traces)} traces")

            # Get existing semantic memories for context
            existing_memories = await ctx.memory_manager.get_semantic_memories(limit=50)

            # Run LLM consolidation
            digest = await self._run_consolidation(ctx, traces, events, existing_memories)

            # Process the digest
            digests_created = 0
            memories_created = 0

            # Create L1 trace digests
            for trace_digest in digest.get("trace_digests", []):
                # Validate required fields
                if not all(k in trace_digest for k in ["trace_id", "topic", "digest"]):
                    logger.warning(f"Skipping invalid trace digest: {trace_digest}")
                    continue
                await ctx.memory_manager.create_l1_digest(
                    trace_id=trace_digest["trace_id"],
                    topic=trace_digest["topic"],
                    digest=trace_digest["digest"],
                    source_event_ids=[],  # Could extract from events
                )
                digests_created += 1

            # Create semantic memories
            trace_id_strs = [str(t.trace_id) for t in traces]
            for memory_update in digest.get("semantic_memory_updates", []):
                # Validate required fields
                if not all(k in memory_update for k in ["claim", "confidence", "provenance_event_ids"]):
                    logger.warning(f"Skipping invalid memory update: {memory_update}")
                    continue
                await ctx.memory_manager.create_semantic_memory(
                    claim=memory_update["claim"],
                    confidence=memory_update["confidence"],
                    provenance_event_ids=memory_update["provenance_event_ids"],
                    source_trace_ids=trace_id_strs,
                )
                memories_created += 1

            # Record the digest
            self._add_event(ctx, EventType.SLEEP_DIGEST, digest)

            # Record memory consolidation summary
            self._add_event(ctx, EventType.MEMORY_CONSOLIDATION, {
                "digests_created": digests_created,
                "memories_created": memories_created,
                "trace_count": len(traces),
                "event_count": len(events),
            })

            # Record sleep end
            completed_at = datetime.now(timezone.utc)
            self._add_event(ctx, EventType.SLEEP_END, {
                "sleep_id": sleep_id,
                "completed_at": completed_at.isoformat(),
                "duration_seconds": (completed_at - started_at).total_seconds(),
            })

            # Persist all events
            await self._persist_events(ctx)
            await session.commit()

            logger.info(f"Sleep consolidation complete: {digests_created} digests, {memories_created} memories")

            return SleepResult(
                sleep_id=sleep_id,
                started_at=started_at,
                completed_at=completed_at,
                traces_processed=len(traces),
                events_processed=len(events),
                digests_created=digests_created,
                memories_created=memories_created,
                open_questions=digest.get("open_questions", []),
                goal_updates=digest.get("goal_updates", []),
            )

        except Exception as e:
            logger.exception(f"Sleep consolidation failed: {e}")
            return SleepResult(
                sleep_id=sleep_id,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                traces_processed=0,
                events_processed=0,
                digests_created=0,
                memories_created=0,
                open_questions=[],
                goal_updates=[],
                error=str(e),
            )

    async def _get_traces_for_consolidation(
        self,
        ctx: ConsolidationContext,
    ) -> Sequence[TraceModel]:
        """Get traces from the sleep window that need consolidation."""
        cutoff = ctx.started_at - timedelta(hours=self.settings.sleep_window_hours)

        # Query traces from the window that are completed
        query = (
            select(TraceModel)
            .where(TraceModel.started_at >= cutoff)
            .where(TraceModel.completed_at.isnot(None))
            .order_by(TraceModel.started_at)
        )

        result = await ctx.session.execute(query)
        return result.scalars().all()

    async def _fetch_events_for_traces(
        self,
        ctx: ConsolidationContext,
        traces: Sequence[TraceModel],
    ) -> list[EventModel]:
        """Fetch events for the given traces."""
        all_events = []

        for trace in traces:
            events = await ctx.event_repo.list_by_trace(trace.trace_id)
            all_events.extend(events)

            # Respect batch limit
            if len(all_events) >= self.settings.max_events_per_batch:
                logger.warning(f"Hit max events limit ({self.settings.max_events_per_batch})")
                break

        return all_events

    async def _run_consolidation(
        self,
        ctx: ConsolidationContext,
        traces: Sequence[TraceModel],
        events: list[EventModel],
        existing_memories: Sequence,
    ) -> dict[str, Any]:
        """Run the LLM consolidation prompt."""
        # Format sleep window
        start_time = min(t.started_at for t in traces)
        end_time = max(t.completed_at or t.started_at for t in traces)
        sleep_window = f"{start_time.isoformat()} to {end_time.isoformat()}"

        # Format trace IDs
        trace_ids = [str(t.trace_id) for t in traces]

        # Format events as JSONL blob
        events_blob = self._format_events_blob(events)

        # Format existing memories
        semantic_snapshot = ctx.memory_manager.format_semantic_for_context(existing_memories)

        # Load and render prompt
        prompt_config = ctx.prompts.load("sleep_consolidation")
        messages = render_prompt(prompt_config, {
            "sleep_window": sleep_window,
            "trace_ids": json.dumps(trace_ids),
            "events_blob": events_blob,
            "semantic_memory_snapshot": semantic_snapshot,
        })

        # Call LLM
        response = await ctx.llm.complete(
            messages=messages,
            provider=self.settings.llm_primary_provider,
            model=self.settings.llm_primary_model,
            json_mode=True,
            temperature=0.3,  # Lower temperature for consolidation
            max_tokens=4096,
        )

        # Parse response
        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse consolidation response: {e}")
            return {
                "date_range": sleep_window,
                "trace_digests": [],
                "semantic_memory_updates": [],
                "open_questions": [],
                "goal_updates": [],
            }

    def _format_events_blob(self, events: list[EventModel]) -> str:
        """Format events as a JSONL blob for the prompt."""
        lines = []

        for event in events:
            # Create a compact representation
            entry = {
                "id": str(event.event_id)[:8],
                "actor": event.actor,
                "type": event.event_type,
            }

            # Add content
            if event.content_text:
                entry["text"] = event.content_text[:500]  # Truncate
            if event.content_json:
                # Only include key fields from JSON
                content = event.content_json
                if isinstance(content, dict):
                    # Extract summary fields if they exist
                    for key in ["message", "summary", "topic", "workspace_summary"]:
                        if key in content:
                            entry[key] = content[key]

            lines.append(json.dumps(entry))

        return "\n".join(lines)

    def _add_event(
        self,
        ctx: ConsolidationContext,
        event_type: EventType,
        content: dict[str, Any],
    ) -> None:
        """Add an event to the persistence queue."""
        # Sleep events don't have a normal trace_id - use a synthetic one
        # This is a design choice - sleep could have its own trace or be system-level
        synthetic_trace_id = UUID("00000000-0000-0000-0000-000000000000")

        event = EventCreate(
            trace_id=synthetic_trace_id,
            actor=Actor.SLEEP,
            stream=Stream.SLEEP,
            event_type=event_type,
            content_json=content,
        )
        ctx.events_to_persist.append(event)

    async def _persist_events(self, ctx: ConsolidationContext) -> None:
        """Persist all queued events to the database."""
        if not ctx.events_to_persist:
            return

        # Need a trace for the events to reference
        # Create a synthetic "sleep trace"
        synthetic_trace = TraceModel(
            trace_id=UUID("00000000-0000-0000-0000-000000000000"),
            input_type="user_message",  # Use a valid input type
            started_at=ctx.started_at,
            completed_at=datetime.now(timezone.utc),
        )

        # Check if synthetic trace exists, if not create it
        existing = await ctx.trace_repo.get(synthetic_trace.trace_id)
        if not existing:
            ctx.session.add(synthetic_trace)
            await ctx.session.flush()

        # Create events
        await ctx.event_repo.create_many(ctx.events_to_persist)
        logger.info(f"Persisted {len(ctx.events_to_persist)} sleep events")
