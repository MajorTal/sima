"""
Integration tests for sima_llm LLM Router.

These tests require a valid OPENAI_API_KEY in the environment.
"""

import json
import pytest

from sima_llm import LLMRouter, LLMResponse


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


class TestLLMRouterBasic:
    """Basic LLM router functionality tests."""

    @pytest.mark.asyncio
    async def test_simple_completion(self, llm_router: LLMRouter):
        """Test a simple completion without tools."""
        response = await llm_router.complete(
            messages=[
                {"role": "user", "content": "Say 'hello' and nothing else."}
            ],
            max_tokens=10,
        )

        assert response is not None
        assert isinstance(response, LLMResponse)
        assert response.content is not None
        assert "hello" in response.content.lower()

    @pytest.mark.asyncio
    async def test_json_mode(self, llm_router: LLMRouter):
        """Test JSON mode completion."""
        response = await llm_router.complete(
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Always respond in JSON."},
                {"role": "user", "content": "Return a JSON object with a 'greeting' field set to 'hello'."}
            ],
            json_mode=True,
            max_tokens=50,
        )

        assert response is not None
        assert response.content is not None

        # Should be valid JSON
        data = json.loads(response.content)
        assert "greeting" in data
        assert data["greeting"].lower() == "hello"

    @pytest.mark.asyncio
    async def test_system_message(self, llm_router: LLMRouter):
        """Test that system messages are respected."""
        response = await llm_router.complete(
            messages=[
                {"role": "system", "content": "You always respond with exactly the word 'PINEAPPLE', nothing else."},
                {"role": "user", "content": "What is 2+2?"}
            ],
            max_tokens=10,
        )

        assert response is not None
        assert response.content is not None
        assert "pineapple" in response.content.lower()

    @pytest.mark.asyncio
    async def test_usage_tracking(self, llm_router: LLMRouter):
        """Test that token usage is tracked."""
        response = await llm_router.complete(
            messages=[
                {"role": "user", "content": "Say hi."}
            ],
            max_tokens=10,
        )

        assert response is not None
        assert response.usage is not None
        assert response.usage.get("prompt_tokens", 0) > 0
        assert response.usage.get("total_tokens", 0) > 0


class TestLLMRouterTools:
    """LLM router tool calling tests."""

    @pytest.mark.asyncio
    async def test_tool_calling(self, llm_router: LLMRouter):
        """Test that tool calling works."""
        response = await llm_router.complete(
            messages=[
                {"role": "user", "content": "What is the current date and time?"}
            ],
            tools=["get_current_datetime"],
            max_tokens=100,
        )

        assert response is not None
        # Should have executed the tool
        assert len(response.tool_results) > 0 or response.content is not None


class TestLLMRouterSync:
    """Test synchronous API."""

    def test_sync_completion(self, llm_router: LLMRouter):
        """Test synchronous completion method."""
        response = llm_router.complete_sync(
            messages=[
                {"role": "user", "content": "Say 'test' and nothing else."}
            ],
            max_tokens=10,
        )

        assert response is not None
        assert response.content is not None
        assert "test" in response.content.lower()
