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
import uuid
from dataclasses import dataclass, field
from typing import Any

from .module_runner import ModuleRunner, ModuleResult
from .settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class TraceContext:
    """Context for a single cognitive trace."""

    trace_id: str
    input_type: str
    message_text: str | None = None
    tick_metadata: dict[str, Any] | None = None
    chat_id: int | None = None
    from_user: dict[str, Any] | None = None

    # Results from modules
    percept: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    selected_items: list[dict[str, Any]] = field(default_factory=list)
    workspace: dict[str, Any] | None = None
    metacog: dict[str, Any] | None = None
    attention_schema: dict[str, Any] | None = None
    speaker_output: dict[str, Any] | None = None

    # Control flags
    suppress_output: bool = False


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
    ):
        """
        Initialize the awake loop.

        Args:
            settings: Configuration settings.
            module_runner: Module runner for executing cognitive modules.
        """
        self.settings = settings or Settings()
        self.module_runner = module_runner

        # Cognitive parameters
        self.recurrence_steps = self.settings.recurrence_steps
        self.workspace_capacity = self.settings.workspace_capacity

        # State
        self.current_goal: str = "Understand and assist the user."
        self.recent_workspaces: list[dict] = []
        self.recent_messages: list[dict] = []

    def run_message(
        self,
        input_type: str,
        message_text: str,
        chat_id: int | None = None,
        from_user: dict | None = None,
    ) -> TraceContext:
        """
        Run the awake loop for a user message.

        Args:
            input_type: Type of input ("user_message").
            message_text: The user's message text.
            chat_id: Telegram chat ID.
            from_user: User info from Telegram.

        Returns:
            TraceContext with all module results.
        """
        return asyncio.run(
            self._run_async(
                input_type=input_type,
                message_text=message_text,
                chat_id=chat_id,
                from_user=from_user,
            )
        )

    def run_tick(
        self,
        input_type: str,
        tick_metadata: dict[str, Any],
    ) -> TraceContext:
        """
        Run the awake loop for a tick event.

        Args:
            input_type: Type of input ("minute_tick" or "autonomous_tick").
            tick_metadata: Tick information (timestamp, hour, minute, etc.).

        Returns:
            TraceContext with all module results.
        """
        return asyncio.run(
            self._run_async(
                input_type=input_type,
                tick_metadata=tick_metadata,
            )
        )

    async def _run_async(
        self,
        input_type: str,
        message_text: str | None = None,
        tick_metadata: dict[str, Any] | None = None,
        chat_id: int | None = None,
        from_user: dict | None = None,
    ) -> TraceContext:
        """
        Async implementation of the awake loop.
        """
        trace_id = str(uuid.uuid4())

        ctx = TraceContext(
            trace_id=trace_id,
            input_type=input_type,
            message_text=message_text,
            tick_metadata=tick_metadata,
            chat_id=chat_id,
            from_user=from_user,
        )

        logger.info(f"Starting awake loop, trace_id={trace_id}, input_type={input_type}")

        try:
            # Step 1: Perception
            await self._run_perception(ctx)

            # Check suppress_output from perception
            if ctx.percept and ctx.percept.get("suppress_output", False):
                ctx.suppress_output = True
                logger.info(
                    f"Suppressing output for trace {trace_id} "
                    f"(reason: {ctx.percept.get('temporal_context', {}).get('time_significance_reason', 'routine tick')})"
                )

            # For suppressed ticks, we can optionally run reduced processing
            if ctx.suppress_output and input_type == "minute_tick":
                # Log the event but skip full cognitive loop
                await self._persist_event(ctx, "perception", ctx.percept)
                logger.info(f"Tick suppressed, skipping full cognitive loop for trace {trace_id}")
                return ctx

            # Step 2: Parallel candidate generation
            await self._run_candidate_modules(ctx)

            # Step 3: Attention gate (select top-K)
            await self._run_attention_gate(ctx)

            # Step 4: Workspace integration
            await self._run_workspace_integrator(ctx)

            # Step 5: Metacognition
            await self._run_metacognition(ctx)

            # Step 6: Attention schema update
            await self._run_attention_schema(ctx)

            # Step 7: Speaker (if not suppressed)
            if not ctx.suppress_output:
                await self._run_speaker(ctx)

                # Step 8: Send external message
                if ctx.speaker_output:
                    await self._send_telegram_message(ctx)

            # Persist final state
            await self._persist_trace(ctx)

            logger.info(f"Awake loop complete, trace_id={trace_id}")

        except Exception as e:
            logger.exception(f"Error in awake loop: {e}")
            raise

        return ctx

    async def _run_perception(self, ctx: TraceContext) -> None:
        """Run the perception module."""
        if self.module_runner is None:
            logger.warning("No module runner configured, skipping perception")
            return

        variables = {
            "trace_id": ctx.trace_id,
            "recurrence_steps": self.recurrence_steps,
            "input_type": ctx.input_type,
            "recent_external_messages": self.recent_messages[-5:],
            "recent_workspace_summaries": [
                w.get("workspace_summary", "") for w in self.recent_workspaces[-3:]
            ],
            "current_goal": self.current_goal,
        }

        # Add input-specific variables
        if ctx.input_type == "user_message":
            variables["incoming_message_text"] = ctx.message_text or ""
        elif ctx.tick_metadata:
            variables.update(ctx.tick_metadata)

        result = await self.module_runner.run("perception_rpt", variables)

        if result.is_valid:
            ctx.percept = result.output
        else:
            logger.error(f"Perception validation failed: {result.validation_errors}")
            ctx.percept = result.output  # Use anyway for debugging

    async def _run_candidate_modules(self, ctx: TraceContext) -> None:
        """Run parallel candidate generation modules."""
        if self.module_runner is None:
            return

        modules = ["memory_retrieval", "planner", "critic"]
        tasks = []

        base_variables = {
            "trace_id": ctx.trace_id,
            "current_goal": self.current_goal,
            "percept_json": ctx.percept,
            "recent_workspace_summaries": [
                w.get("workspace_summary", "") for w in self.recent_workspaces[-3:]
            ],
        }

        for module in modules:
            variables = base_variables.copy()
            if module == "memory_retrieval":
                variables["retrieved_snippets"] = []  # Would come from vector DB

            tasks.append(self.module_runner.run(module, variables))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for module, result in zip(modules, results):
            if isinstance(result, Exception):
                logger.error(f"Module {module} failed: {result}")
            elif isinstance(result, ModuleResult) and result.is_valid:
                ctx.candidates.extend(result.output.get("candidates", []))

    async def _run_attention_gate(self, ctx: TraceContext) -> None:
        """Run the attention gate to select top-K candidates."""
        if self.module_runner is None:
            return

        variables = {
            "trace_id": ctx.trace_id,
            "workspace_capacity": self.workspace_capacity,
            "candidates_json": ctx.candidates,
        }

        result = await self.module_runner.run("attention_gate", variables)

        if result.is_valid:
            ctx.selected_items = result.output.get("selected", [])
        else:
            # Fallback: take top K by salience
            sorted_candidates = sorted(
                ctx.candidates,
                key=lambda x: x.get("salience", 0),
                reverse=True,
            )
            ctx.selected_items = sorted_candidates[: self.workspace_capacity]

    async def _run_workspace_integrator(self, ctx: TraceContext) -> None:
        """Run the workspace integrator."""
        if self.module_runner is None:
            return

        variables = {
            "trace_id": ctx.trace_id,
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

    async def _run_metacognition(self, ctx: TraceContext) -> None:
        """Run the metacognition module."""
        if self.module_runner is None:
            return

        variables = {
            "trace_id": ctx.trace_id,
            "percept_json": ctx.percept,
            "workspace_json": ctx.workspace,
            "recent_metacog_reports": [],
        }

        result = await self.module_runner.run("metacog_hot", variables)

        if result.is_valid:
            ctx.metacog = result.output

    async def _run_attention_schema(self, ctx: TraceContext) -> None:
        """Run the attention schema module."""
        if self.module_runner is None:
            return

        variables = {
            "trace_id": ctx.trace_id,
            "percept_json": ctx.percept,
            "selected_items_json": ctx.selected_items,
            "workspace_json": ctx.workspace,
            "prior_attention_schema": None,
        }

        result = await self.module_runner.run("attention_schema_ast", variables)

        if result.is_valid:
            ctx.attention_schema = result.output

    async def _run_speaker(self, ctx: TraceContext) -> None:
        """Run the speaker module."""
        if self.module_runner is None:
            return

        variables = {
            "trace_id": ctx.trace_id,
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

        logger.info(f"Would send Telegram message: {message[:100]}...")

        # Store in recent messages
        self.recent_messages.append({
            "role": "assistant",
            "content": message,
            "trace_id": ctx.trace_id,
        })
        if len(self.recent_messages) > 20:
            self.recent_messages = self.recent_messages[-20:]

    async def _persist_event(
        self,
        ctx: TraceContext,
        event_type: str,
        content: dict | None,
    ) -> None:
        """Persist a single event to the database."""
        logger.debug(f"Persisting event: {event_type} for trace {ctx.trace_id}")
        # Would persist to database here

    async def _persist_trace(self, ctx: TraceContext) -> None:
        """Persist the complete trace."""
        logger.debug(f"Persisting trace: {ctx.trace_id}")
        # Would persist all events to database here


class Settings:
    """Awake loop settings."""

    def __init__(self):
        import os

        self.recurrence_steps = int(os.environ.get("RECURRENCE_STEPS", "3"))
        self.workspace_capacity = int(os.environ.get("WORKSPACE_CAPACITY_K", "7"))
        self.minute_tick_enabled = (
            os.environ.get("MINUTE_TICK_ENABLED", "false").lower() == "true"
        )
        self.timezone = os.environ.get("TIMEZONE", "UTC")
