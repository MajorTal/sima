"""
Integration tests for The Brain's ModuleRunner.

These tests require a valid OPENAI_API_KEY in the environment.
"""

import pytest

from sima_llm import LLMRouter
from sima_prompts import PromptRegistry
from sima_brain import ModuleRunner, ModuleResult


@pytest.fixture
def llm_router(openai_api_key: str | None) -> LLMRouter:
    """Create an LLM router instance."""
    if not openai_api_key:
        pytest.skip("OPENAI_API_KEY not set")

    return LLMRouter(
        primary_provider="openai",
        primary_model="gpt-4o-mini",
        api_keys={"openai": openai_api_key},
    )


@pytest.fixture
def module_runner(llm_router: LLMRouter, project_root) -> ModuleRunner:
    """Create a ModuleRunner instance."""
    return ModuleRunner(
        llm_router=llm_router,
        prompt_registry=PromptRegistry(),
        schemas_dir=project_root,
    )


class TestModuleRunnerBasic:
    """Basic ModuleRunner functionality tests."""

    @pytest.mark.asyncio
    async def test_run_perception_module(self, module_runner: ModuleRunner):
        """Test running the perception module."""
        variables = {
            "trace_id": "test-trace-123",
            "recurrence_steps": 2,
            "input_type": "user_message",
            "incoming_message_text": "Hello, how are you today?",
            "recent_external_messages": [],
            "recent_workspace_summaries": [],
            "current_goal": "Understand and assist the user.",
        }

        result = await module_runner.run(
            module_name="perception_rpt",
            variables=variables,
            temperature=0.5,
            max_tokens=1000,
        )

        assert result is not None
        assert isinstance(result, ModuleResult)
        assert result.module_name == "perception_rpt"
        assert result.output is not None

        # Check for expected fields in perception output
        output = result.output
        assert "summary" in output or "intents" in output or "confidence" in output

    @pytest.mark.asyncio
    async def test_run_attention_gate_module(self, module_runner: ModuleRunner):
        """Test running the attention gate module."""
        variables = {
            "trace_id": "test-trace-123",
            "workspace_capacity": 5,
            "candidates_json": [
                {
                    "source": "memory",
                    "content": "Previous conversation about weather",
                    "salience": 0.7,
                    "reasoning": "Related to current topic",
                },
                {
                    "source": "planner",
                    "content": "Suggest checking forecast",
                    "salience": 0.8,
                    "reasoning": "Actionable suggestion",
                },
            ],
        }

        result = await module_runner.run(
            module_name="attention_gate",
            variables=variables,
            temperature=0.3,
            max_tokens=500,
        )

        assert result is not None
        assert isinstance(result, ModuleResult)
        assert result.module_name == "attention_gate"

        # Should have selected items
        if result.is_valid:
            assert "selected" in result.output

    @pytest.mark.asyncio
    async def test_run_speaker_module(self, module_runner: ModuleRunner):
        """Test running the speaker module."""
        variables = {
            "trace_id": "test-trace-123",
            "workspace_json": {
                "workspace_summary": "User greeted and asked about the day.",
                "next_actions": ["Respond warmly"],
            },
            "external_draft": "Hello! I'm doing well, thanks for asking.",
        }

        result = await module_runner.run(
            module_name="speaker",
            variables=variables,
            temperature=0.7,
            max_tokens=300,
        )

        assert result is not None
        assert isinstance(result, ModuleResult)
        assert result.module_name == "speaker"

        # Should have a message in output
        if result.is_valid:
            assert "message" in result.output


class TestModuleRunnerSync:
    """Test synchronous API."""

    def test_run_sync(self, module_runner: ModuleRunner):
        """Test synchronous run method."""
        variables = {
            "trace_id": "test-trace-sync",
            "recurrence_steps": 1,
            "input_type": "user_message",
            "incoming_message_text": "Test message",
            "recent_external_messages": [],
            "recent_workspace_summaries": [],
            "current_goal": "Test goal",
        }

        result = module_runner.run_sync(
            module_name="perception_rpt",
            variables=variables,
            max_tokens=500,
        )

        assert result is not None
        assert isinstance(result, ModuleResult)
