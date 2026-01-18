"""
LLM Router - Multi-provider routing with tool calling support.

This router handles:
- Provider selection (OpenAI, Google, xAI, Bedrock)
- Tool calling with automatic execution and continuation
- Response parsing and validation
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .tools import execute_tool, get_tool_definitions

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM completion."""

    content: str | None
    """The text content of the response."""

    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    """List of tool calls made by the model."""

    tool_results: list[dict[str, Any]] = field(default_factory=list)
    """Results from executed tool calls."""

    finish_reason: str = "stop"
    """Reason the model stopped generating."""

    usage: dict[str, int] = field(default_factory=dict)
    """Token usage statistics."""

    raw_response: Any = None
    """Raw provider response for debugging."""


@dataclass
class Message:
    """Chat message."""

    role: str
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for API calls."""
        d = {"role": self.role}
        if self.content is not None:
            d["content"] = self.content
        if self.tool_calls is not None:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            d["name"] = self.name
        return d


class LLMRouter:
    """
    Multi-provider LLM router with tool calling support.

    Supports automatic tool execution and conversation continuation.
    """

    def __init__(
        self,
        primary_provider: str = "openai",
        primary_model: str = "gpt-4o",
        fast_provider: str | None = None,
        fast_model: str | None = None,
        api_keys: dict[str, str] | None = None,
        max_tool_iterations: int = 5,
    ):
        """
        Initialize the LLM router.

        Args:
            primary_provider: Default provider (openai, google, xai, bedrock).
            primary_model: Default model ID.
            fast_provider: Provider for fast/cheap completions.
            fast_model: Model for fast/cheap completions.
            api_keys: Dict of provider -> API key.
            max_tool_iterations: Max tool call rounds before stopping.
        """
        self.primary_provider = primary_provider
        self.primary_model = primary_model
        self.fast_provider = fast_provider or primary_provider
        self.fast_model = fast_model or primary_model
        self.api_keys = api_keys or {}
        self.max_tool_iterations = max_tool_iterations

        # Provider clients (lazy initialized)
        self._clients: dict[str, Any] = {}

    def _get_client(self, provider: str) -> Any:
        """Get or create a client for the given provider."""
        if provider in self._clients:
            return self._clients[provider]

        if provider == "openai":
            try:
                from openai import OpenAI

                client = OpenAI(api_key=self.api_keys.get("openai"))
                self._clients[provider] = client
                return client
            except ImportError:
                raise ImportError("openai package required for OpenAI provider")
        elif provider == "google":
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.api_keys.get("google"))
                self._clients[provider] = genai
                return genai
            except ImportError:
                raise ImportError("google-generativeai package required for Google provider")
        elif provider == "xai":
            try:
                from openai import OpenAI

                client = OpenAI(
                    api_key=self.api_keys.get("xai"),
                    base_url="https://api.x.ai/v1",
                )
                self._clients[provider] = client
                return client
            except ImportError:
                raise ImportError("openai package required for xAI provider")
        elif provider == "bedrock":
            try:
                import boto3

                client = boto3.client("bedrock-runtime")
                self._clients[provider] = client
                return client
            except ImportError:
                raise ImportError("boto3 package required for Bedrock provider")
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[str] | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
        auto_execute_tools: bool = True,
    ) -> LLMResponse:
        """
        Complete a conversation with optional tool calling.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: List of tool names to make available (e.g., ['get_current_datetime']).
            provider: Provider to use (defaults to primary_provider).
            model: Model to use (defaults to primary_model).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            json_mode: Request JSON output format.
            auto_execute_tools: If True, automatically execute tool calls and continue.

        Returns:
            LLMResponse with content and any tool call information.
        """
        provider = provider or self.primary_provider
        model = model or self.primary_model

        # Get tool definitions
        tool_definitions = get_tool_definitions(tools) if tools else None

        # Build conversation
        conversation = [Message(**m) if isinstance(m, dict) else m for m in messages]
        all_tool_results: list[dict[str, Any]] = []

        for iteration in range(self.max_tool_iterations):
            response = await self._call_provider(
                provider=provider,
                model=model,
                messages=[m.to_dict() for m in conversation],
                tools=tool_definitions,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )

            # If no tool calls or we don't auto-execute, return response
            if not response.tool_calls or not auto_execute_tools:
                response.tool_results = all_tool_results
                return response

            # Execute tool calls
            assistant_msg = Message(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls,
            )
            conversation.append(assistant_msg)

            for tool_call in response.tool_calls:
                tool_name = tool_call.get("function", {}).get("name", "")
                arguments_str = tool_call.get("function", {}).get("arguments", "{}")
                tool_call_id = tool_call.get("id", "")

                try:
                    arguments = json.loads(arguments_str) if arguments_str else {}
                except json.JSONDecodeError:
                    arguments = {}

                logger.info(f"Executing tool: {tool_name} with args: {arguments}")

                try:
                    result = execute_tool(tool_name, arguments)
                    result_str = json.dumps(result)
                    all_tool_results.append(
                        {
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": result,
                        }
                    )
                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    result_str = json.dumps({"error": str(e)})
                    all_tool_results.append(
                        {
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "error": str(e),
                        }
                    )

                # Add tool result to conversation
                tool_result_msg = Message(
                    role="tool",
                    content=result_str,
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
                conversation.append(tool_result_msg)

            # Continue to next iteration

        # Max iterations reached
        final_response = await self._call_provider(
            provider=provider,
            model=model,
            messages=[m.to_dict() for m in conversation],
            tools=None,  # No more tools for final response
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        )
        final_response.tool_results = all_tool_results
        return final_response

    async def _call_provider(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LLMResponse:
        """Call a specific provider."""
        if provider in ("openai", "xai"):
            return await self._call_openai_compatible(
                provider=provider,
                model=model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        elif provider == "google":
            return await self._call_google(
                model=model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        elif provider == "bedrock":
            return await self._call_bedrock(
                model=model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _call_openai_compatible(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LLMResponse:
        """Call OpenAI-compatible API (OpenAI, xAI)."""
        client = self._get_client(provider)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )

        return LLMResponse(
            content=choice.message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            raw_response=response,
        )

    async def _call_google(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LLMResponse:
        """Call Google Generative AI API."""
        genai = self._get_client("google")

        # Convert messages to Google format
        google_messages = []
        system_instruction = None

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                google_messages.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                google_messages.append({"role": "model", "parts": [msg.get("content", "")]})
            elif msg["role"] == "tool":
                # Handle tool results
                google_messages.append(
                    {
                        "role": "function",
                        "parts": [
                            {
                                "function_response": {
                                    "name": msg.get("name", ""),
                                    "response": json.loads(msg.get("content", "{}")),
                                }
                            }
                        ],
                    }
                )

        # Convert tools to Google format
        google_tools = None
        if tools:
            google_tools = [
                {
                    "function_declarations": [
                        {
                            "name": t["function"]["name"],
                            "description": t["function"]["description"],
                            "parameters": t["function"]["parameters"],
                        }
                        for t in tools
                    ]
                }
            ]

        model_instance = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_instruction,
        )

        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if json_mode:
            generation_config.response_mime_type = "application/json"

        response = model_instance.generate_content(
            google_messages,
            generation_config=generation_config,
            tools=google_tools,
        )

        # Extract tool calls from response
        tool_calls = []
        content = None

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "function_call"):
                    fc = part.function_call
                    tool_calls.append(
                        {
                            "id": f"call_{fc.name}",
                            "type": "function",
                            "function": {
                                "name": fc.name,
                                "arguments": json.dumps(dict(fc.args)),
                            },
                        }
                    )
                elif hasattr(part, "text"):
                    content = part.text

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason="stop",
            usage={},
            raw_response=response,
        )

    async def _call_bedrock(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> LLMResponse:
        """Call AWS Bedrock API."""
        client = self._get_client("bedrock")

        # Convert messages to Bedrock format (Claude)
        system_parts = []
        bedrock_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_parts.append({"text": msg["content"]})
            elif msg["role"] == "user":
                bedrock_messages.append({"role": "user", "content": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                content = []
                if msg.get("content"):
                    content.append({"text": msg["content"]})
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        content.append(
                            {
                                "toolUse": {
                                    "toolUseId": tc["id"],
                                    "name": tc["function"]["name"],
                                    "input": json.loads(tc["function"]["arguments"]),
                                }
                            }
                        )
                bedrock_messages.append({"role": "assistant", "content": content})
            elif msg["role"] == "tool":
                bedrock_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "toolResult": {
                                    "toolUseId": msg.get("tool_call_id", ""),
                                    "content": [{"json": json.loads(msg.get("content", "{}"))}],
                                }
                            }
                        ],
                    }
                )

        # Convert tools to Bedrock format
        tool_config = None
        if tools:
            tool_config = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": t["function"]["name"],
                            "description": t["function"]["description"],
                            "inputSchema": {"json": t["function"]["parameters"]},
                        }
                    }
                    for t in tools
                ]
            }

        request = {
            "modelId": model,
            "messages": bedrock_messages,
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens,
            },
        }

        if system_parts:
            request["system"] = system_parts
        if tool_config:
            request["toolConfig"] = tool_config

        response = client.converse(**request)

        # Parse response
        tool_calls = []
        content = None

        for block in response.get("output", {}).get("message", {}).get("content", []):
            if "text" in block:
                content = block["text"]
            elif "toolUse" in block:
                tu = block["toolUse"]
                tool_calls.append(
                    {
                        "id": tu["toolUseId"],
                        "type": "function",
                        "function": {
                            "name": tu["name"],
                            "arguments": json.dumps(tu["input"]),
                        },
                    }
                )

        usage = response.get("usage", {})

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.get("stopReason", "stop"),
            usage={
                "prompt_tokens": usage.get("inputTokens", 0),
                "completion_tokens": usage.get("outputTokens", 0),
                "total_tokens": usage.get("inputTokens", 0) + usage.get("outputTokens", 0),
            },
            raw_response=response,
        )

    def complete_sync(
        self,
        messages: list[dict[str, Any]],
        tools: list[str] | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
        auto_execute_tools: bool = True,
    ) -> LLMResponse:
        """
        Synchronous version of complete().

        See complete() for parameter documentation.
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            return asyncio.run(
                self.complete(
                    messages=messages,
                    tools=tools,
                    provider=provider,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                    auto_execute_tools=auto_execute_tools,
                )
            )
        else:
            # Running in async context, use thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.complete(
                        messages=messages,
                        tools=tools,
                        provider=provider,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        json_mode=json_mode,
                        auto_execute_tools=auto_execute_tools,
                    ),
                )
                return future.result()
