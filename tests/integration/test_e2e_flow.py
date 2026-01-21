"""
End-to-end integration tests for the complete SIMA flow.

Tests the full M0 pipeline:
    Telegram webhook → SQS → Brain → DB → API

This file tests the complete flow with mocked LLM responses,
verifying that events are properly created, persisted, and retrievable.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from sima_core.types import Actor, EventType, InputType, Stream
from sima_storage.database import get_session, init_db, close_db
from sima_storage.repository import TraceRepository, EventRepository

logger = logging.getLogger(__name__)


# ============================================================================
# Mock LLM Infrastructure
# ============================================================================


@dataclass
class MockLLMResponse:
    """Mock LLM response matching the real LLMResponse interface."""
    content: str
    tool_results: list = None
    usage: dict = None
    model: str = "mock-model"
    provider: str = "mock"

    def __post_init__(self):
        if self.tool_results is None:
            self.tool_results = []
        if self.usage is None:
            self.usage = {"input_tokens": 10, "output_tokens": 20}


class MockLLMRouter:
    """
    Mock LLM router that returns predefined responses for each module.

    Returns valid JSON responses that pass schema validation.
    """

    # Predefined responses for each module (matching actual JSON schemas)
    MODULE_RESPONSES = {
        "perception_rpt": {
            "summary": "User sent a greeting message",
            "intents": ["greeting", "social"],
            "entities": [],
            "questions": [],
            "confidence": 0.9,
            "input_type": "user_message",
            "suppress_output": False,
            "temporal_context": {
                "is_time_significant": False,
                "time_significance_reason": ""
            },
            "recurrence": {
                "steps": 2,
                "stability_score": 0.85,
                "revisions": [
                    {"step": 1, "delta_summary": "Initial parse of greeting"},
                    {"step": 2, "delta_summary": "Refined understanding"},
                ]
            },
            "representation": {
                "topics": ["greeting", "social_interaction"],
                "claims": [
                    {
                        "claim": "User is initiating a friendly conversation",
                        "support": "Explicit greeting in message",
                        "uncertainty": "low"
                    }
                ],
                "constraints": []
            },
        },
        "memory_retrieval": {
            "module": "memory",
            "candidates": [
                {
                    "id": "mem-1",
                    "kind": "memory",
                    "content": "Previous conversation about similar topic",
                    "salience": 0.6,
                    "rationale": "Related context from past interaction",
                }
            ],
        },
        "planner": {
            "module": "planner",
            "candidates": [
                {
                    "id": "plan-1",
                    "kind": "plan",
                    "content": "Respond with a friendly greeting",
                    "salience": 0.8,
                    "rationale": "Appropriate response to greeting",
                }
            ],
        },
        "critic": {
            "module": "critic",
            "candidates": [
                {
                    "id": "crit-1",
                    "kind": "critique",
                    "content": "Response should be warm but concise",
                    "salience": 0.7,
                    "rationale": "Quality guidance for response",
                }
            ],
        },
        "attention_gate": {
            "selected": [
                {
                    "id": "plan-1",
                    "kind": "plan",
                    "content": "Respond with a friendly greeting",
                    "salience": 0.8,
                }
            ],
            "rejected": [],
            "selection_rationale": "Planner suggestion most relevant",
        },
        "workspace_integrator": {
            "workspace_summary": "User greeted, should respond warmly",
            "items": [
                {
                    "id": "plan-1",
                    "content": "Respond with a friendly greeting",
                    "why_in_workspace": "Primary action to take",
                }
            ],
            "current_goal": "Respond to user greeting warmly",
            "next_actions": ["send_response"],
            "broadcast_message": "User greeted, preparing friendly response",
            "external_draft": "Hello! It's nice to hear from you.",
        },
        "metacog_hot": {
            "confidence": 0.85,
            "uncertainties": [],
            "hallucination_risks": [],
            "belief_updates": [],
        },
        "attention_schema_ast": {
            "current_focus": ["user_greeting", "response_planning"],
            "predicted_next_focus": ["plan-1"],
            "control_suggestions": ["Maintain focus on response"],
            "prediction_notes": "Expecting to focus on response execution",
        },
        "speaker": {
            # Schema uses message_text, but awake_loop code uses "message" - include both
            "message_text": "Hello! It's wonderful to hear from you. How can I help you today?",
            "message": "Hello! It's wonderful to hear from you. How can I help you today?",
        },
        "inner_monologue": {
            "inner_monologue": "A user greeted me warmly. I feel engaged and ready to help.",
            "clarity": 0.9,
            "key_observations": ["User is friendly", "Simple greeting interaction"],
            "emotional_valence": "positive",
        },
    }

    def __init__(self, **kwargs):
        """Accept any kwargs to match real LLMRouter signature."""
        pass

    async def complete(
        self,
        messages: list,
        tools: list | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
        auto_execute_tools: bool = False,
    ) -> MockLLMResponse:
        """
        Return a mock response based on the prompt content.

        Detects which module is being called by examining the messages.
        """
        # Detect module from system message content
        system_msg = next((m for m in messages if m.get("role") == "system"), None)
        if not system_msg:
            return MockLLMResponse(content="{}")

        content = system_msg.get("content", "")

        # Map system message content to module
        module_name = None
        for name in self.MODULE_RESPONSES:
            if name.replace("_", " ") in content.lower() or name in content.lower():
                module_name = name
                break

        # Fallback detection based on keywords
        if not module_name:
            if "perception" in content.lower() or "recurrence" in content.lower():
                module_name = "perception_rpt"
            elif "memory" in content.lower() or "retrieval" in content.lower():
                module_name = "memory_retrieval"
            elif "planner" in content.lower() or "plan" in content.lower():
                module_name = "planner"
            elif "critic" in content.lower():
                module_name = "critic"
            elif "attention gate" in content.lower() or "select" in content.lower():
                module_name = "attention_gate"
            elif "workspace" in content.lower() or "integrat" in content.lower():
                module_name = "workspace_integrator"
            elif "metacog" in content.lower() or "higher-order" in content.lower():
                module_name = "metacog_hot"
            elif "attention schema" in content.lower() or "ast" in content.lower():
                module_name = "attention_schema_ast"
            elif "speaker" in content.lower() or "speak" in content.lower():
                module_name = "speaker"
            elif "monologue" in content.lower() or "inner" in content.lower():
                module_name = "inner_monologue"

        response_data = self.MODULE_RESPONSES.get(module_name, {})
        return MockLLMResponse(content=json.dumps(response_data))


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def setup_db(database_url):
    """Initialize database connection for tests."""
    os.environ["DATABASE_URL"] = database_url
    await init_db()
    yield
    await close_db()


@pytest.fixture
def mock_llm_router():
    """Create a mock LLM router."""
    return MockLLMRouter()


@pytest.fixture
def mock_telegram_client():
    """Create a mock Telegram client."""
    client = MagicMock()
    client.send_event = AsyncMock()
    client.reply_to_user = AsyncMock()
    return client


@pytest.fixture
def mock_settings():
    """Create mock settings for The Brain."""
    settings = MagicMock()
    settings.telegram_bot_token = ""
    settings.telegram_telemetry_enabled = False
    settings.recurrence_steps = 2
    settings.workspace_capacity = 5
    settings.competition_iterations = 5
    settings.belief_revision_threshold = 0.4
    settings.max_belief_revision_iterations = 2
    settings.database_url = "postgresql+asyncpg://sima:sima_dev@localhost:5432/sima"
    return settings


# ============================================================================
# E2E Flow Tests
# ============================================================================


@pytest.mark.asyncio
class TestE2EAwakeLoop:
    """
    Test the complete awake loop flow with mocked LLM.

    This tests M0 acceptance criteria:
    - Single message produces external reply
    - Conscious stream post
    - Subconscious stream post
    - Events persisted
    """

    async def test_full_awake_loop_flow(self, setup_db, mock_llm_router, mock_telegram_client, mock_settings, project_root):
        """Test the complete awake loop from message to persistence."""
        from sima_prompts import PromptRegistry
        from sima_brain.module_runner import ModuleRunner
        from sima_brain.awake_loop import AwakeLoop

        # Create module runner with mock LLM
        module_runner = ModuleRunner(
            llm_router=mock_llm_router,
            prompt_registry=PromptRegistry(),
            schemas_dir=project_root,
        )

        # Create awake loop
        awake_loop = AwakeLoop(
            settings=mock_settings,
            module_runner=module_runner,
            telegram_client=mock_telegram_client,
        )

        # Run the awake loop with a test message
        ctx = await awake_loop._run_async(
            input_type=InputType.USER_MESSAGE,
            message_text="Hello, how are you?",
            chat_id=12345,
            message_id=1,
            from_user={"id": 12345, "first_name": "Test", "username": "testuser"},
        )

        # Verify trace context was populated
        assert ctx.trace_id is not None
        assert ctx.percept is not None
        assert ctx.workspace is not None
        assert ctx.metacog is not None
        assert ctx.speaker_output is not None
        assert ctx.inner_monologue is not None

        # Verify perception ran
        assert ctx.percept.get("summary") is not None
        assert ctx.percept.get("recurrence", {}).get("stability_score") is not None

        # Verify workspace was populated
        assert ctx.workspace.get("workspace_summary") is not None

        # Verify speaker produced output (code uses "message", schema uses "message_text")
        assert ctx.speaker_output.get("message") is not None or ctx.speaker_output.get("message_text") is not None

        # Verify inner monologue ran
        assert ctx.inner_monologue.get("inner_monologue") is not None

        # Verify events were persisted to database
        async with get_session() as session:
            trace_repo = TraceRepository(session)
            event_repo = EventRepository(session)

            # Check trace exists
            trace = await trace_repo.get(ctx.trace_id)
            assert trace is not None
            assert trace.input_type == InputType.USER_MESSAGE

            # Check events exist
            events = await event_repo.list_by_trace(ctx.trace_id)
            assert len(events) > 0

            # Should have events from multiple actors
            actors = {e.actor for e in events}
            assert Actor.PERCEPTION in actors
            assert Actor.WORKSPACE in actors

            # Should have events in different streams
            streams = {e.stream for e in events}
            assert Stream.SUBCONSCIOUS in streams
            assert Stream.CONSCIOUS in streams

    async def test_suppressed_tick_still_generates_monologue(self, setup_db, mock_llm_router, mock_telegram_client, mock_settings, project_root):
        """Test that suppressed ticks still generate inner monologue."""
        from sima_prompts import PromptRegistry
        from sima_brain.module_runner import ModuleRunner
        from sima_brain.awake_loop import AwakeLoop

        # Override perception response to suppress output
        suppressed_response = {
            "summary": "Routine minute tick - nothing significant",
            "intents": [],
            "entities": [],
            "questions": [],
            "confidence": 0.9,
            "input_type": "minute_tick",
            "suppress_output": True,
            "temporal_context": {
                "is_time_significant": False,
                "time_significance_reason": "routine tick"
            },
            "recurrence": {
                "steps": 2,
                "stability_score": 0.9,
                "revisions": []
            },
            "representation": {
                "topics": ["time_awareness"],
                "claims": [],
                "constraints": []
            },
        }

        # Create a custom mock router that returns suppressed perception
        class SuppressedMockRouter(MockLLMRouter):
            MODULE_RESPONSES = {
                **MockLLMRouter.MODULE_RESPONSES,
                "perception_rpt": suppressed_response,
            }

        module_runner = ModuleRunner(
            llm_router=SuppressedMockRouter(),
            prompt_registry=PromptRegistry(),
            schemas_dir=project_root,
        )

        awake_loop = AwakeLoop(
            settings=mock_settings,
            module_runner=module_runner,
            telegram_client=mock_telegram_client,
        )

        # Run with minute tick
        ctx = await awake_loop._run_async(
            input_type=InputType.MINUTE_TICK,
            tick_metadata={
                "input_type": "minute_tick",
                "tick_hour": 14,
                "tick_minute": 30,
            },
        )

        # Should be suppressed
        assert ctx.suppress_output is True

        # But inner monologue should still have run
        assert ctx.inner_monologue is not None

        # Verify events persisted
        async with get_session() as session:
            event_repo = EventRepository(session)
            events = await event_repo.list_by_trace(ctx.trace_id)

            # Should have perception and monologue events
            event_types = {e.event_type for e in events}
            assert EventType.PERCEPT in event_types
            assert EventType.MONOLOGUE in event_types

    async def test_candidates_flow_through_attention_gate(self, setup_db, mock_llm_router, mock_telegram_client, mock_settings, project_root):
        """Test that candidates from parallel modules flow through attention gate."""
        from sima_prompts import PromptRegistry
        from sima_brain.module_runner import ModuleRunner
        from sima_brain.awake_loop import AwakeLoop

        module_runner = ModuleRunner(
            llm_router=mock_llm_router,
            prompt_registry=PromptRegistry(),
            schemas_dir=project_root,
        )

        awake_loop = AwakeLoop(
            settings=mock_settings,
            module_runner=module_runner,
            telegram_client=mock_telegram_client,
        )

        ctx = await awake_loop._run_async(
            input_type=InputType.USER_MESSAGE,
            message_text="What's the weather like?",
            chat_id=12345,
            message_id=2,
        )

        # Should have selected items from attention gate
        assert len(ctx.selected_items) > 0

        # Verify selection event was recorded
        async with get_session() as session:
            event_repo = EventRepository(session)
            events = await event_repo.list_by_trace(ctx.trace_id)

            selection_events = [
                e for e in events
                if e.event_type == EventType.SELECTION
            ]
            assert len(selection_events) == 1

            # Selection should have competition telemetry
            selection = selection_events[0]
            assert selection.content_json is not None
            assert "workspace_capacity_k" in selection.content_json


@pytest.mark.asyncio
class TestE2EPersistence:
    """Test event persistence and retrieval."""

    async def test_trace_and_events_persist_correctly(self, setup_db, mock_llm_router, mock_telegram_client, mock_settings, project_root):
        """Test that traces and events are persisted with correct data."""
        from sima_prompts import PromptRegistry
        from sima_brain.module_runner import ModuleRunner
        from sima_brain.awake_loop import AwakeLoop

        module_runner = ModuleRunner(
            llm_router=mock_llm_router,
            prompt_registry=PromptRegistry(),
            schemas_dir=project_root,
        )

        awake_loop = AwakeLoop(
            settings=mock_settings,
            module_runner=module_runner,
            telegram_client=mock_telegram_client,
        )

        test_message = "Tell me a joke"
        ctx = await awake_loop._run_async(
            input_type=InputType.USER_MESSAGE,
            message_text=test_message,
            chat_id=54321,
            message_id=42,
        )

        async with get_session() as session:
            trace_repo = TraceRepository(session)
            event_repo = EventRepository(session)

            # Verify trace data
            trace = await trace_repo.get(ctx.trace_id)
            assert trace.user_message == test_message
            assert trace.telegram_chat_id == 54321
            assert trace.telegram_message_id == 42
            assert trace.completed_at is not None

            # Verify response was recorded
            assert trace.response_message is not None

            # Verify all expected events exist
            events = await event_repo.list_by_trace(ctx.trace_id)

            # Count events by actor
            actor_counts = {}
            for e in events:
                actor_counts[e.actor] = actor_counts.get(e.actor, 0) + 1

            # Should have events from perception, workspace, metacog, etc.
            assert Actor.PERCEPTION in actor_counts
            assert Actor.WORKSPACE in actor_counts
            assert Actor.METACOG in actor_counts

    async def test_events_can_be_filtered_by_stream(self, setup_db, mock_llm_router, mock_telegram_client, mock_settings, project_root):
        """Test that events can be filtered by stream."""
        from sima_prompts import PromptRegistry
        from sima_brain.module_runner import ModuleRunner
        from sima_brain.awake_loop import AwakeLoop

        module_runner = ModuleRunner(
            llm_router=mock_llm_router,
            prompt_registry=PromptRegistry(),
            schemas_dir=project_root,
        )

        awake_loop = AwakeLoop(
            settings=mock_settings,
            module_runner=module_runner,
            telegram_client=mock_telegram_client,
        )

        ctx = await awake_loop._run_async(
            input_type=InputType.USER_MESSAGE,
            message_text="Hello",
            chat_id=11111,
            message_id=1,
        )

        async with get_session() as session:
            event_repo = EventRepository(session)

            # Filter by conscious stream
            conscious_events = await event_repo.list_by_trace(
                ctx.trace_id, stream=Stream.CONSCIOUS
            )

            # Should have workspace and monologue events
            for e in conscious_events:
                assert e.stream == Stream.CONSCIOUS

            # Filter by subconscious stream
            subconscious_events = await event_repo.list_by_trace(
                ctx.trace_id, stream=Stream.SUBCONSCIOUS
            )

            for e in subconscious_events:
                assert e.stream == Stream.SUBCONSCIOUS


@pytest.mark.asyncio
class TestE2EWebhookToSQS:
    """Test the ingest-api webhook to SQS flow."""

    async def test_webhook_enqueues_to_sqs(self, sqs_queue_url, aws_endpoint_url):
        """Test that webhook correctly enqueues messages to SQS."""
        import boto3
        from botocore.exceptions import EndpointConnectionError

        # Skip if LocalStack is not available
        try:
            sqs = boto3.client(
                "sqs",
                region_name="us-east-1",
                endpoint_url=aws_endpoint_url,
            )
            # Try to get queue attributes to verify connection
            sqs.get_queue_attributes(
                QueueUrl=sqs_queue_url,
                AttributeNames=["ApproximateNumberOfMessages"]
            )
        except (EndpointConnectionError, Exception) as e:
            pytest.skip(f"LocalStack SQS not available: {e}")

        # Test SQS enqueue directly
        from sima_ingest.sqs import enqueue_telegram_update

        # Set up environment for ingest
        os.environ["AWS_ENDPOINT_URL"] = aws_endpoint_url
        os.environ["SQS_QUEUE_URL"] = sqs_queue_url

        # Need to reload sqs module to pick up new settings
        import importlib
        from sima_ingest import settings as ingest_settings
        from sima_ingest import sqs as sqs_module

        # Update settings
        object.__setattr__(ingest_settings.settings, "aws_endpoint_url", aws_endpoint_url)
        object.__setattr__(ingest_settings.settings, "sqs_queue_url", sqs_queue_url)

        # Clear cached client
        sqs_module._sqs_client = None

        # Create a test Telegram update
        test_update = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {"id": 12345, "first_name": "Test", "username": "testuser"},
                "chat": {"id": 12345, "type": "private"},
                "date": 1234567890,
                "text": "Hello from e2e test!",
            }
        }

        # Enqueue the update
        message_id = enqueue_telegram_update(test_update)
        assert message_id is not None
        assert len(message_id) > 0

        # Verify message is in queue
        response = sqs.receive_message(
            QueueUrl=sqs_queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
        )

        messages = response.get("Messages", [])
        assert len(messages) > 0

        # Parse and verify message content
        body = json.loads(messages[0]["Body"])
        assert body["event_type"] == "telegram_update"
        assert body["update"]["message"]["text"] == "Hello from e2e test!"

        # Clean up - delete the message
        sqs.delete_message(
            QueueUrl=sqs_queue_url,
            ReceiptHandle=messages[0]["ReceiptHandle"],
        )


@pytest.mark.asyncio
class TestE2EWorkerProcessing:
    """Test the SQS worker message processing."""

    async def test_worker_processes_telegram_update(self, setup_db, mock_llm_router, mock_settings, project_root):
        """Test that worker correctly processes a Telegram update message via direct awake loop call."""
        from sima_prompts import PromptRegistry
        from sima_brain.module_runner import ModuleRunner
        from sima_brain.awake_loop import AwakeLoop

        module_runner = ModuleRunner(
            llm_router=mock_llm_router,
            prompt_registry=PromptRegistry(),
            schemas_dir=project_root,
        )

        awake_loop = AwakeLoop(
            settings=mock_settings,
            module_runner=module_runner,
            telegram_client=None,
        )

        # Simulate processing a Telegram update by calling awake loop directly
        # (avoiding the worker's asyncio.run() call that conflicts with pytest-asyncio)
        ctx = await awake_loop._run_async(
            input_type=InputType.USER_MESSAGE,
            message_text="Test from worker",
            chat_id=99999,
            message_id=99,
            from_user={"id": 99999, "first_name": "Worker", "username": "workertest"},
        )

        # Verify trace was created in database
        async with get_session() as session:
            trace_repo = TraceRepository(session)
            trace = await trace_repo.get(ctx.trace_id)

            assert trace is not None
            assert trace.user_message == "Test from worker"
            assert trace.telegram_chat_id == 99999

    async def test_worker_processes_minute_tick(self, setup_db, mock_llm_router, mock_settings, project_root):
        """Test that worker correctly processes minute tick events via direct awake loop call."""
        from sima_prompts import PromptRegistry
        from sima_brain.module_runner import ModuleRunner
        from sima_brain.awake_loop import AwakeLoop

        # Use suppressed perception for tick
        suppressed_response = {
            "summary": "Routine minute tick - nothing significant",
            "intents": [],
            "entities": [],
            "questions": [],
            "confidence": 0.9,
            "input_type": "minute_tick",
            "suppress_output": True,
            "temporal_context": {
                "is_time_significant": False,
                "time_significance_reason": "routine tick"
            },
            "recurrence": {
                "steps": 2,
                "stability_score": 0.9,
                "revisions": []
            },
            "representation": {
                "topics": ["time_awareness"],
                "claims": [],
                "constraints": []
            },
        }

        class TickMockRouter(MockLLMRouter):
            MODULE_RESPONSES = {
                **MockLLMRouter.MODULE_RESPONSES,
                "perception_rpt": suppressed_response,
            }

        module_runner = ModuleRunner(
            llm_router=TickMockRouter(),
            prompt_registry=PromptRegistry(),
            schemas_dir=project_root,
        )

        awake_loop = AwakeLoop(
            settings=mock_settings,
            module_runner=module_runner,
            telegram_client=None,
        )

        # Simulate minute tick by calling awake loop directly
        ctx = await awake_loop._run_async(
            input_type=InputType.MINUTE_TICK,
            tick_metadata={
                "input_type": "minute_tick",
                "tick_hour": 14,
                "tick_minute": 30,
            },
        )

        # Verify trace was created
        async with get_session() as session:
            trace_repo = TraceRepository(session)
            trace = await trace_repo.get(ctx.trace_id)

            assert trace is not None
            assert trace.input_type == InputType.MINUTE_TICK


# ============================================================================
# Integration with API Layer
# ============================================================================


def is_api_running() -> bool:
    """Check if the API server is running."""
    try:
        import httpx
        response = httpx.get("http://localhost:8001/health", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.mark.asyncio
class TestE2EAPIRetrieval:
    """Test that events persisted by The Brain can be retrieved via API."""

    @pytest.fixture(autouse=True)
    def check_api_running(self):
        """Skip tests if API is not running."""
        if not is_api_running():
            pytest.skip("API server not running at localhost:8001")

    async def test_api_returns_persisted_trace(self, setup_db, mock_llm_router, mock_telegram_client, mock_settings, project_root):
        """Test that API can retrieve traces created by The Brain."""
        import httpx
        from sima_prompts import PromptRegistry
        from sima_brain.module_runner import ModuleRunner
        from sima_brain.awake_loop import AwakeLoop

        module_runner = ModuleRunner(
            llm_router=mock_llm_router,
            prompt_registry=PromptRegistry(),
            schemas_dir=project_root,
        )

        awake_loop = AwakeLoop(
            settings=mock_settings,
            module_runner=module_runner,
            telegram_client=mock_telegram_client,
        )

        # Run awake loop to create a trace
        unique_message = f"E2E API test {uuid4()}"
        ctx = await awake_loop._run_async(
            input_type=InputType.USER_MESSAGE,
            message_text=unique_message,
            chat_id=77777,
            message_id=77,
        )

        # Query API for the trace
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8001/traces/{ctx.trace_id}"
            )

            # Should be able to retrieve the trace
            # Note: API may require auth, so 401 is acceptable
            if response.status_code == 200:
                data = response.json()
                assert data["trace_id"] == str(ctx.trace_id)
                assert data["user_message"] == unique_message
            elif response.status_code != 401:
                pytest.fail(f"Unexpected status code: {response.status_code}")

    async def test_api_returns_events_for_trace(self, setup_db, mock_llm_router, mock_telegram_client, mock_settings, project_root):
        """Test that API can retrieve events for a trace."""
        import httpx
        from sima_prompts import PromptRegistry
        from sima_brain.module_runner import ModuleRunner
        from sima_brain.awake_loop import AwakeLoop

        module_runner = ModuleRunner(
            llm_router=mock_llm_router,
            prompt_registry=PromptRegistry(),
            schemas_dir=project_root,
        )

        awake_loop = AwakeLoop(
            settings=mock_settings,
            module_runner=module_runner,
            telegram_client=mock_telegram_client,
        )

        ctx = await awake_loop._run_async(
            input_type=InputType.USER_MESSAGE,
            message_text="API events test",
            chat_id=88888,
            message_id=88,
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8001/traces/{ctx.trace_id}/events"
            )

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)
                assert len(data) > 0

                # Verify events have expected structure
                for event in data:
                    assert "event_id" in event
                    assert "actor" in event
                    assert "stream" in event
            elif response.status_code != 401:
                pytest.fail(f"Unexpected status code: {response.status_code}")
