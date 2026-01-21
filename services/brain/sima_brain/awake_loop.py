"""
Awake Loop - The main cognitive loop for SIMA.

Implements the workspace-centric cognitive architecture:
1. Perception (RPT): Build structured representation with recurrence
2. Parallel modules: Generate candidates (memory, planner, critic)
3. Attention gate: Select top-K items for workspace
4. Workspace integrator: Broadcast selected contents
5. Metacognition: Produce higher-order reports
6. Speaker: Generate external message (if not suppressed)
7. Persist all events

For time-based inputs (minute_tick), respects suppress_output flag
to skip external message generation for routine ticks.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sima_core.ids import generate_id
from sima_core.types import Actor, EventType, InputType, Stream

from sima_storage.database import close_db, get_session
from sima_storage.repository import MemoryRepository

from .module_runner import ModuleRunner, ModuleResult
from .persistence import TracePersistence, create_trace, persist_trace, get_prior_attention_prediction, get_recent_monologues
from .settings import Settings
from .simulated_competition import run_competition
from .telegram import TelegramClient

logger = logging.getLogger(__name__)


@dataclass
class TraceContext:
    """Context for a single cognitive trace."""

    trace_id: UUID
    input_type: InputType
    message_text: str | None = None
    tick_metadata: dict[str, Any] | None = None
    chat_id: int | None = None
    message_id: int | None = None
    from_user: dict[str, Any] | None = None

    # Results from modules
    percept: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    selected_items: list[dict[str, Any]] = field(default_factory=list)
    workspace: dict[str, Any] | None = None
    metacog: dict[str, Any] | None = None
    attention_schema: dict[str, Any] | None = None
    speaker_output: dict[str, Any] | None = None
    inner_monologue: dict[str, Any] | None = None

    # Control flags
    suppress_output: bool = False

    # Persistence
    persistence: TracePersistence | None = None


class AwakeLoop:
    """
    The awake cognitive loop.

    Orchestrates module execution and handles suppress_output
    for time-based ticks.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        module_runner: ModuleRunner | None = None,
        telegram_client: TelegramClient | None = None,
    ):
        """
        Initialize the awake loop.

        Args:
            settings: Configuration settings.
            module_runner: Module runner for executing cognitive modules.
            telegram_client: Telegram client for sending messages.
        """
        self.settings = settings or Settings()
        self.module_runner = module_runner
        self.telegram_client = telegram_client

        # Cognitive parameters
        self.recurrence_steps = self.settings.recurrence_steps
        self.workspace_capacity = self.settings.workspace_capacity

        # State
        self.current_goal: str = "Understand and assist the user."
        self.recent_workspaces: list[dict] = []
        self.recent_messages: list[dict] = []

    async def _post_telemetry(
        self,
        ctx: TraceContext,
        stream: Stream,
        event_type: str,
        actor: str,
        content: dict | str | None,
    ) -> None:
        """
        Post telemetry to the appropriate Telegram channel.

        Only posts if telegram_telemetry_enabled is True.
        """
        if not self.settings.telegram_telemetry_enabled:
            return

        if not self.telegram_client:
            return

        await self.telegram_client.send_event(
            stream=stream,
            event_type=event_type,
            actor=actor,
            content=content,
            trace_id=str(ctx.trace_id),
        )

    def run_message(
        self,
        message_text: str,
        chat_id: int | None = None,
        message_id: int | None = None,
        from_user: dict | None = None,
    ) -> TraceContext:
        """
        Run the awake loop for a user message.

        Args:
            message_text: The user's message text.
            chat_id: Telegram chat ID.
            message_id: Telegram message ID.
            from_user: User info from Telegram.

        Returns:
            TraceContext with all module results.
        """
        # Close any existing DB connections to avoid event loop conflicts
        asyncio.run(close_db())
        return asyncio.run(
            self._run_async(
                input_type=InputType.USER_MESSAGE,
                message_text=message_text,
                chat_id=chat_id,
                message_id=message_id,
                from_user=from_user,
            )
        )

    def run_tick(
        self,
        input_type: InputType,
        tick_metadata: dict[str, Any],
    ) -> TraceContext:
        """
        Run the awake loop for a tick event.

        Args:
            input_type: Type of input (MINUTE_TICK or AUTONOMOUS_TICK).
            tick_metadata: Tick information (timestamp, hour, minute, etc.).

        Returns:
            TraceContext with all module results.
        """
        # Close any existing DB connections to avoid event loop conflicts
        asyncio.run(close_db())
        return asyncio.run(
            self._run_async(
                input_type=input_type,
                tick_metadata=tick_metadata,
            )
        )

    async def _run_async(
        self,
        input_type: InputType,
        message_text: str | None = None,
        tick_metadata: dict[str, Any] | None = None,
        chat_id: int | None = None,
        message_id: int | None = None,
        from_user: dict | None = None,
    ) -> TraceContext:
        """
        Async implementation of the awake loop.
        """
        trace_id = generate_id()

        ctx = TraceContext(
            trace_id=trace_id,
            input_type=input_type,
            message_text=message_text,
            tick_metadata=tick_metadata,
            chat_id=chat_id,
            message_id=message_id,
            from_user=from_user,
            persistence=TracePersistence(trace_id),
        )

        logger.info(f"Starting awake loop, trace_id={trace_id}, input_type={input_type.value}")

        try:
            # Create trace in database
            await create_trace(
                trace_id=trace_id,
                input_type=input_type,
                telegram_chat_id=chat_id,
                telegram_message_id=message_id,
                user_message=message_text,
            )

            # Record input event
            ctx.persistence.add_input_event(
                input_type=input_type,
                content_text=message_text,
                content_json=tick_metadata,
            )

            # Step 1: Perception
            await self._run_perception(ctx)

            # Check suppress_output from perception
            if ctx.percept and ctx.percept.get("suppress_output", False):
                ctx.suppress_output = True
                logger.info(
                    f"Suppressing output for trace {trace_id} "
                    f"(reason: {ctx.percept.get('temporal_context', {}).get('time_significance_reason', 'routine tick')})"
                )

            # For suppressed ticks, run reduced processing but still generate inner monologue
            if ctx.suppress_output and input_type == InputType.MINUTE_TICK:
                # Still run inner monologue for suppressed ticks (always happens)
                await self._run_inner_monologue(ctx)
                # Persist what we have and return
                await persist_trace(ctx.persistence)
                logger.info(f"Tick suppressed, ran inner monologue only for trace {trace_id}")
                return ctx

            # Step 2: Parallel candidate generation
            await self._run_candidate_modules(ctx)

            # Step 3: Attention gate (select top-K)
            await self._run_attention_gate(ctx)

            # Step 4: Workspace integration
            await self._run_workspace_integrator(ctx)

            # Step 5: Metacognition with belief revision loop
            await self._run_metacognition(ctx)

            # Step 5b: HOT Belief Revision Loop
            # If metacognition reports low confidence, re-run earlier modules
            await self._run_belief_revision_loop(ctx)

            # Step 6: Attention schema update
            await self._run_attention_schema(ctx)

            # Step 7: Speaker (if not suppressed)
            response_message: str | None = None
            if not ctx.suppress_output:
                await self._run_speaker(ctx)

                # Step 8: Send external message
                if ctx.speaker_output:
                    response_message = ctx.speaker_output.get("message")
                    await self._send_telegram_message(ctx)

            # Step 9: Inner Monologue (ALWAYS runs, even when output is suppressed)
            await self._run_inner_monologue(ctx)

            # Persist final state
            await persist_trace(ctx.persistence, response_message)

            logger.info(f"Awake loop complete, trace_id={trace_id}")

        except Exception as e:
            logger.exception(f"Error in awake loop: {e}")
            # Record error event
            if ctx.persistence:
                ctx.persistence.add_event(
                    actor=Actor.SYSTEM,
                    stream=Stream.SUBCONSCIOUS,
                    event_type=EventType.ERROR,
                    content_text=str(e),
                )
                await persist_trace(ctx.persistence)
            raise

        return ctx

    async def _run_perception(self, ctx: TraceContext) -> None:
        """Run the perception module."""
        if self.module_runner is None:
            logger.warning("No module runner configured, skipping perception")
            return

        variables = {
            "trace_id": str(ctx.trace_id),
            "recurrence_steps": self.recurrence_steps,
            "input_type": ctx.input_type.value,
            "recent_external_messages": self.recent_messages[-5:],
            "recent_workspace_summaries": [
                w.get("workspace_summary", "") for w in self.recent_workspaces[-3:]
            ],
            "current_goal": self.current_goal,
        }

        # Add input-specific variables
        if ctx.input_type == InputType.USER_MESSAGE:
            variables["incoming_message_text"] = ctx.message_text or ""
        elif ctx.tick_metadata:
            variables.update(ctx.tick_metadata)

        result = await self.module_runner.run("perception_rpt", variables)

        if result.is_valid:
            ctx.percept = result.output
        else:
            logger.error(f"Perception validation failed: {result.validation_errors}")
            ctx.percept = result.output  # Use anyway for debugging

        # Record perception event
        if ctx.persistence and ctx.percept:
            ctx.persistence.add_module_event(
                actor=Actor.PERCEPTION,
                event_type=EventType.PERCEPT,
                output=ctx.percept,
            )

        # Post to subconscious Telegram channel
        if ctx.percept:
            await self._post_telemetry(
                ctx,
                Stream.SUBCONSCIOUS,
                "percept",
                "perception",
                ctx.percept,
            )

    async def _run_candidate_modules(self, ctx: TraceContext) -> None:
        """Run parallel candidate generation modules."""
        if self.module_runner is None:
            return

        modules = ["memory_retrieval", "planner", "critic"]
        module_actors = {
            "memory_retrieval": Actor.MEMORY,
            "planner": Actor.PLANNER,
            "critic": Actor.CRITIC,
        }
        tasks = []

        base_variables = {
            "trace_id": str(ctx.trace_id),
            "current_goal": self.current_goal,
            "percept_json": ctx.percept,
            "recent_workspace_summaries": [
                w.get("workspace_summary", "") for w in self.recent_workspaces[-3:]
            ],
        }

        # Retrieve memories from database for memory_retrieval module
        retrieved_snippets = await self._retrieve_memories(ctx)

        for module in modules:
            variables = base_variables.copy()
            if module == "memory_retrieval":
                variables["retrieved_snippets"] = retrieved_snippets

            tasks.append(self.module_runner.run(module, variables))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for module, result in zip(modules, results):
            if isinstance(result, Exception):
                logger.error(f"Module {module} failed: {result}")
            elif isinstance(result, ModuleResult) and result.is_valid:
                ctx.candidates.extend(result.output.get("candidates", []))

                # Record candidate event
                if ctx.persistence:
                    ctx.persistence.add_module_event(
                        actor=module_actors[module],
                        event_type=EventType.CANDIDATE,
                        output=result.output,
                    )

                # Post to subconscious Telegram channel
                await self._post_telemetry(
                    ctx,
                    Stream.SUBCONSCIOUS,
                    "candidate",
                    module,
                    result.output,
                )

    async def _retrieve_memories(self, ctx: TraceContext) -> list[dict]:
        """
        Retrieve memories from the database for the cognitive loop.

        Loads:
        - L3 core memories (always available, including genesis)
        - Recent L1 trace digests
        - L2 consolidated memories (when available)

        Returns a list of memory snippets for the memory_retrieval module.
        """
        retrieved_snippets = []

        try:
            async with get_session() as session:
                repo = MemoryRepository(session)

                # Always load L3 core memories (genesis, stable beliefs)
                l3_memories = await repo.list_by_type("L3", limit=10)
                for m in l3_memories:
                    retrieved_snippets.append({
                        "id": str(m.memory_id),
                        "type": m.memory_type,
                        "level": "L3",
                        "content": m.content,
                        "relevance_score": m.relevance_score,
                        "category": m.metadata_json.get("category") if m.metadata_json else None,
                    })

                # Load recent L1 trace digests
                l1_memories = await repo.list_by_type("L1", limit=20)
                for m in l1_memories:
                    retrieved_snippets.append({
                        "id": str(m.memory_id),
                        "type": m.memory_type,
                        "level": "L1",
                        "content": m.content,
                        "relevance_score": m.relevance_score,
                    })

                # Load L2 consolidated memories if available
                l2_memories = await repo.list_by_type("L2", limit=10)
                for m in l2_memories:
                    retrieved_snippets.append({
                        "id": str(m.memory_id),
                        "type": m.memory_type,
                        "level": "L2",
                        "content": m.content,
                        "relevance_score": m.relevance_score,
                    })

            logger.debug(
                f"Retrieved {len(retrieved_snippets)} memories: "
                f"{len(l3_memories)} L3, {len(l1_memories)} L1, {len(l2_memories)} L2"
            )

        except Exception as e:
            logger.warning(f"Failed to retrieve memories: {e}")
            # Continue without memories rather than failing the loop

        return retrieved_snippets

    async def _run_attention_gate(self, ctx: TraceContext) -> None:
        """
        Run the attention gate using simulated competition.

        Uses biologically-inspired mutual inhibition dynamics instead of
        LLM-as-judge ranking. This avoids the "homunculus problem" where
        a judge module needs to know what's important.

        Candidates compete for workspace access based on:
        - Initial salience (activation)
        - Self-excitation (winners keep winning)
        - Lateral inhibition (similar candidates suppress each other)
        """
        if not ctx.candidates:
            logger.warning("No candidates to select from, skipping attention gate")
            return

        # Run the simulated competition algorithm
        competition_result = run_competition(
            candidates=ctx.candidates,
            workspace_capacity=self.workspace_capacity,
            iterations=self.settings.competition_iterations,
        )

        ctx.selected_items = competition_result.selected

        # Record selection event with competition telemetry
        if ctx.persistence:
            ctx.persistence.add_module_event(
                actor=Actor.ATTENTION_GATE,
                event_type=EventType.SELECTION,
                output={
                    "workspace_capacity_k": self.workspace_capacity,
                    "selected": ctx.selected_items,
                    "selected_ids": [c.get("id") for c in competition_result.selected],
                    "rejected_ids": [c.get("id") for c in competition_result.rejected],
                    "selection_rationale": competition_result.selection_rationale,
                    "competition_trace": competition_result.competition_trace,
                    "iterations_run": competition_result.iterations_run,
                    "convergence_delta": competition_result.convergence_delta,
                    "inhibition_events": competition_result.inhibition_events,
                },
            )

        logger.debug(
            f"Attention gate selected {len(ctx.selected_items)} items "
            f"from {len(ctx.candidates)} candidates "
            f"({competition_result.inhibition_events} inhibition events)"
        )

        # Post to subconscious Telegram channel
        await self._post_telemetry(
            ctx,
            Stream.SUBCONSCIOUS,
            "selection",
            "attention_gate",
            {
                "selected_count": len(ctx.selected_items),
                "rejected_count": len(competition_result.rejected),
                "inhibition_events": competition_result.inhibition_events,
                "selection_rationale": competition_result.selection_rationale,
            },
        )

    async def _run_workspace_integrator(self, ctx: TraceContext) -> None:
        """Run the workspace integrator."""
        if self.module_runner is None:
            return

        variables = {
            "trace_id": str(ctx.trace_id),
            "current_goal": self.current_goal,
            "percept_json": ctx.percept,
            "selected_items_json": ctx.selected_items,
            "metacog_json": ctx.metacog,
            "attention_schema_json": ctx.attention_schema,
        }

        result = await self.module_runner.run("workspace_integrator", variables)

        if result.is_valid:
            ctx.workspace = result.output
            # Update recent workspaces
            self.recent_workspaces.append(ctx.workspace)
            if len(self.recent_workspaces) > 10:
                self.recent_workspaces = self.recent_workspaces[-10:]

            # Record workspace event
            if ctx.persistence:
                ctx.persistence.add_module_event(
                    actor=Actor.WORKSPACE,
                    event_type=EventType.WORKSPACE_UPDATE,
                    output=ctx.workspace,
                )

            # Post to CONSCIOUS Telegram channel (workspace is shared awareness)
            await self._post_telemetry(
                ctx,
                Stream.CONSCIOUS,
                "workspace_update",
                "workspace",
                ctx.workspace,
            )

    async def _run_metacognition(self, ctx: TraceContext) -> None:
        """Run the metacognition module."""
        if self.module_runner is None:
            return

        variables = {
            "trace_id": str(ctx.trace_id),
            "percept_json": ctx.percept,
            "workspace_json": ctx.workspace,
            "recent_metacog_reports": [],
        }

        result = await self.module_runner.run("metacog_hot", variables)

        if result.is_valid:
            ctx.metacog = result.output

            # Record metacognition event
            if ctx.persistence:
                ctx.persistence.add_module_event(
                    actor=Actor.METACOG,
                    event_type=EventType.METACOG_REPORT,
                    output=ctx.metacog,
                )

            # Post to subconscious Telegram channel
            await self._post_telemetry(
                ctx,
                Stream.SUBCONSCIOUS,
                "metacog_report",
                "metacog",
                ctx.metacog,
            )

    async def _run_belief_revision_loop(self, ctx: TraceContext) -> None:
        """
        Run the HOT belief revision loop.

        If metacognition reports low confidence, re-run earlier modules
        to gather more information and revise beliefs. This implements
        the causal coupling requirement of Higher-Order Theories.

        The loop continues until:
        - Confidence rises above threshold, OR
        - Maximum iterations reached, OR
        - Confidence stabilizes (no improvement)
        """
        if not ctx.metacog:
            return

        threshold = self.settings.belief_revision_threshold
        max_iterations = self.settings.max_belief_revision_iterations

        confidence = ctx.metacog.get("confidence", 1.0)
        revision_count = 0
        previous_confidence = confidence

        while (
            confidence < threshold
            and revision_count < max_iterations
        ):
            revision_count += 1
            logger.info(
                f"Belief revision iteration {revision_count}: "
                f"confidence={confidence:.2f} < threshold={threshold:.2f}"
            )

            # Record the belief revision trigger
            belief_revision_event = {
                "iteration": revision_count,
                "trigger_confidence": confidence,
                "threshold": threshold,
                "uncertainties": ctx.metacog.get("uncertainties", []),
                "action": "re-running modules to reduce uncertainty",
            }

            if ctx.persistence:
                ctx.persistence.add_event(
                    actor=Actor.METACOG,
                    stream=Stream.SUBCONSCIOUS,
                    event_type=EventType.BELIEF_REVISION,
                    content_json=belief_revision_event,
                )

            # Post to subconscious Telegram channel
            await self._post_telemetry(
                ctx,
                Stream.SUBCONSCIOUS,
                "belief_revision",
                "metacog",
                belief_revision_event,
            )

            # Re-run candidate generation with uncertainty context
            # Pass the uncertainties from metacog to help focus the search
            await self._run_candidate_modules_with_context(ctx)

            # Re-run attention gate with updated candidates
            await self._run_attention_gate(ctx)

            # Re-run workspace integration
            await self._run_workspace_integrator(ctx)

            # Re-run metacognition to check if confidence improved
            await self._run_metacognition(ctx)

            # Check new confidence
            if ctx.metacog:
                new_confidence = ctx.metacog.get("confidence", 1.0)

                # Check for convergence (confidence not improving)
                if new_confidence <= previous_confidence:
                    logger.info(
                        f"Belief revision converged: confidence={new_confidence:.2f} "
                        f"(was {previous_confidence:.2f})"
                    )
                    break

                previous_confidence = confidence
                confidence = new_confidence

        if revision_count > 0:
            logger.info(
                f"Belief revision complete after {revision_count} iterations: "
                f"final confidence={confidence:.2f}"
            )

    async def _run_candidate_modules_with_context(self, ctx: TraceContext) -> None:
        """
        Run candidate modules with additional context from metacognition.

        This is called during belief revision to focus the candidate
        generation on reducing identified uncertainties.
        """
        if self.module_runner is None:
            return

        modules = ["memory_retrieval", "planner", "critic"]
        module_actors = {
            "memory_retrieval": Actor.MEMORY,
            "planner": Actor.PLANNER,
            "critic": Actor.CRITIC,
        }
        tasks = []

        # Build context with uncertainty focus
        uncertainties = []
        if ctx.metacog:
            uncertainties = ctx.metacog.get("uncertainties", [])

        base_variables = {
            "trace_id": str(ctx.trace_id),
            "current_goal": self.current_goal,
            "percept_json": ctx.percept,
            "recent_workspace_summaries": [
                w.get("workspace_summary", "") for w in self.recent_workspaces[-3:]
            ],
            # Add uncertainty context for focused retrieval
            "uncertainties_to_resolve": uncertainties,
            "is_belief_revision": True,
        }

        # Retrieve memories from database for memory_retrieval module
        retrieved_snippets = await self._retrieve_memories(ctx)

        for module in modules:
            variables = base_variables.copy()
            if module == "memory_retrieval":
                variables["retrieved_snippets"] = retrieved_snippets

            tasks.append(self.module_runner.run(module, variables))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Clear old candidates and add new ones
        ctx.candidates = []

        for module, result in zip(modules, results):
            if isinstance(result, Exception):
                logger.error(f"Module {module} failed during belief revision: {result}")
            elif isinstance(result, ModuleResult) and result.is_valid:
                ctx.candidates.extend(result.output.get("candidates", []))

                # Record candidate event with revision tag
                if ctx.persistence:
                    ctx.persistence.add_module_event(
                        actor=module_actors[module],
                        event_type=EventType.CANDIDATE,
                        output=result.output,
                    )

    async def _run_attention_schema(self, ctx: TraceContext) -> None:
        """
        Run the attention schema module with predict-compare tracking.

        This implements the full AST cycle:
        1. Load prior prediction from previous trace
        2. Compare prior prediction to actual current focus
        3. Calculate control success rate
        4. Generate new prediction for next tick
        """
        if self.module_runner is None:
            return

        # Step 1: Load prior prediction for comparison
        prior_prediction = await get_prior_attention_prediction()

        # Step 2: Compare prior prediction to actual focus (if prior exists)
        if prior_prediction and ctx.selected_items:
            predicted_ids = set(prior_prediction.get("predicted_next_focus", []))
            actual_ids = set(item.get("id", "") for item in ctx.selected_items)

            # Calculate control success rate
            if predicted_ids:
                correct_predictions = predicted_ids & actual_ids
                control_success_rate = len(correct_predictions) / len(predicted_ids)
            else:
                control_success_rate = 0.0

            # Build comparison notes
            if control_success_rate >= 0.8:
                control_notes = "Excellent prediction accuracy. Attention model is well-calibrated."
            elif control_success_rate >= 0.5:
                control_notes = "Moderate prediction accuracy. Some unexpected attention shifts occurred."
            elif control_success_rate > 0:
                control_notes = "Low prediction accuracy. Attention shifted to unexpected items."
            else:
                control_notes = "No overlap between predicted and actual focus. Major attention shift occurred."

            # Record ATTENTION_COMPARISON event
            comparison_event = {
                "prior_prediction": list(predicted_ids),
                "actual_focus": list(actual_ids),
                "control_success_rate": round(control_success_rate, 4),
                "control_notes": control_notes,
                "correct_predictions": list(correct_predictions),
                "missed_predictions": list(predicted_ids - actual_ids),
                "unexpected_focus": list(actual_ids - predicted_ids),
            }

            if ctx.persistence:
                ctx.persistence.add_event(
                    actor=Actor.AST,
                    stream=Stream.SUBCONSCIOUS,
                    event_type=EventType.ATTENTION_COMPARISON,
                    content_json=comparison_event,
                )

            # Post to subconscious Telegram channel
            await self._post_telemetry(
                ctx,
                Stream.SUBCONSCIOUS,
                "attention_comparison",
                "ast",
                comparison_event,
            )

            logger.debug(
                f"AST comparison: success_rate={control_success_rate:.2f}, "
                f"predicted={len(predicted_ids)}, actual={len(actual_ids)}"
            )

        # Step 3: Generate new prediction
        variables = {
            "trace_id": str(ctx.trace_id),
            "percept_json": ctx.percept,
            "selected_ids": [item.get("id", "") for item in ctx.selected_items],
            "selected_items_json": ctx.selected_items,
            "workspace_json": ctx.workspace,
            "previous_attention_schema_json": prior_prediction,
        }

        result = await self.module_runner.run("attention_schema_ast", variables)

        if result.is_valid:
            ctx.attention_schema = result.output

            # Record attention schema prediction event
            if ctx.persistence:
                ctx.persistence.add_module_event(
                    actor=Actor.AST,
                    event_type=EventType.ATTENTION_PREDICTION,
                    output=ctx.attention_schema,
                )

            # Post to subconscious Telegram channel
            await self._post_telemetry(
                ctx,
                Stream.SUBCONSCIOUS,
                "attention_prediction",
                "ast",
                ctx.attention_schema,
            )

    async def _run_speaker(self, ctx: TraceContext) -> None:
        """Run the speaker module."""
        if self.module_runner is None:
            return

        variables = {
            "trace_id": str(ctx.trace_id),
            "workspace_json": ctx.workspace,
            "external_draft": ctx.workspace.get("external_draft", "") if ctx.workspace else "",
        }

        result = await self.module_runner.run("speaker", variables)

        if result.is_valid:
            ctx.speaker_output = result.output

    async def _send_telegram_message(self, ctx: TraceContext) -> None:
        """Send message to Telegram."""
        if not ctx.speaker_output:
            return

        message = ctx.speaker_output.get("message", "")
        if not message:
            return

        # Store in recent messages
        self.recent_messages.append({
            "role": "assistant",
            "content": message,
            "trace_id": str(ctx.trace_id),
        })
        if len(self.recent_messages) > 20:
            self.recent_messages = self.recent_messages[-20:]

        # Send via Telegram client
        if self.telegram_client:
            # Send to external channel (telemetry)
            await self.telegram_client.send_event(
                stream=Stream.EXTERNAL,
                event_type="message_out",
                actor="speaker",
                content=ctx.speaker_output,
                trace_id=str(ctx.trace_id),
            )

            # Reply directly to user if we have their chat ID
            if ctx.chat_id:
                await self.telegram_client.reply_to_user(
                    chat_id=ctx.chat_id,
                    text=message,
                    reply_to_message_id=ctx.message_id,
                )
        else:
            logger.info(f"Would send Telegram message: {message[:100]}...")

        # Record output event
        if ctx.persistence:
            ctx.persistence.add_output_event(message)

        # Send workspace to conscious stream
        if self.telegram_client and ctx.workspace:
            await self.telegram_client.send_event(
                stream=Stream.CONSCIOUS,
                event_type="workspace_update",
                actor="workspace",
                content=ctx.workspace,
                trace_id=str(ctx.trace_id),
            )

    async def _run_inner_monologue(self, ctx: TraceContext) -> None:
        """
        Run the inner monologue module.

        This ALWAYS runs, regardless of suppress_output.
        The inner monologue is Sima's private stream of consciousness,
        reflecting on the current moment of awareness.
        """
        if self.module_runner is None:
            logger.warning("No module runner configured, skipping inner monologue")
            return

        # Build percept summary for the prompt
        percept_summary = ""
        if ctx.percept:
            percept_summary = ctx.percept.get("summary", "")
            if not percept_summary:
                # Fallback to building a summary from available fields
                percept_summary = f"Input type: {ctx.input_type.value}"
                if ctx.message_text:
                    percept_summary += f". User message: {ctx.message_text[:200]}"

        # Get external message if produced
        external_message = ""
        if ctx.speaker_output:
            external_message = ctx.speaker_output.get("message", "")

        # Get previous inner monologue thoughts for continuity
        previous_thoughts = await get_recent_monologues(limit=3)
        # Extract just the inner_monologue text from each, reverse to chronological order
        previous_thoughts_text = []
        for thought in reversed(previous_thoughts):
            monologue_text = thought.get("inner_monologue", "")
            if not monologue_text:
                # Fallback to observations field if inner_monologue not present
                monologue_text = thought.get("observations", "")
            if monologue_text:
                previous_thoughts_text.append(monologue_text)

        variables = {
            "trace_id": str(ctx.trace_id),
            "current_goal": self.current_goal,
            "percept_summary": percept_summary,
            "workspace_json": ctx.workspace,
            "metacog_json": ctx.metacog,
            "attention_schema_json": ctx.attention_schema,
            "external_message": external_message,
            "previous_thoughts": previous_thoughts_text,
        }

        result = await self.module_runner.run("inner_monologue", variables)

        if result.is_valid:
            ctx.inner_monologue = result.output

            # Record monologue event to CONSCIOUS stream
            if ctx.persistence:
                ctx.persistence.add_event(
                    actor=Actor.MONOLOGUE,
                    stream=Stream.CONSCIOUS,
                    event_type=EventType.MONOLOGUE,
                    content_text=ctx.inner_monologue.get("inner_monologue", ""),
                    content_json=ctx.inner_monologue,
                )

            # Send to conscious Telegram channel
            if self.telegram_client:
                await self.telegram_client.send_event(
                    stream=Stream.CONSCIOUS,
                    event_type="monologue",
                    actor="monologue",
                    content=ctx.inner_monologue,
                    trace_id=str(ctx.trace_id),
                )
        else:
            logger.warning(f"Inner monologue validation failed: {result.validation_errors}")
