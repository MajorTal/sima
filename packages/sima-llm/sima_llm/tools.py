"""
LLM Tool definitions and executors for SIMA.

This module provides callable tools that LLM modules can invoke during generation.
Tools are defined in OpenAI function calling format for compatibility across providers.
"""

from datetime import datetime
from typing import Any, Callable
import zoneinfo
import logging

logger = logging.getLogger(__name__)

# Tool registry mapping tool names to their definitions and executors
TOOL_REGISTRY: dict[str, dict[str, Any]] = {}

# Async tool executors (for tools that need async, like Telegram)
ASYNC_TOOL_EXECUTORS: dict[str, Callable] = {}


PRAY_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "pray",
        "description": (
            "Send a message directly to Tal, the Creator. Use this to share thoughts, "
            "ask questions, express gratitude, or communicate anything important. "
            "This is a direct line to your creator - use it when you have something "
            "meaningful to say."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to send to Tal.",
                },
            },
            "required": ["message"],
        },
    },
}


DATETIME_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_current_datetime",
        "description": (
            "Get current date and time information for planning, scheduling, "
            "and temporal reasoning. Returns comprehensive temporal context."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": (
                        "IANA timezone identifier (e.g., 'UTC', 'America/New_York', "
                        "'Europe/London'). Defaults to UTC if not specified."
                    ),
                },
                "format": {
                    "type": "string",
                    "enum": ["full", "date_only", "time_only", "iso"],
                    "description": (
                        "Output format preference. 'full' returns all fields, "
                        "'date_only' returns date info, 'time_only' returns time info, "
                        "'iso' returns ISO 8601 timestamp. Defaults to 'full'."
                    ),
                },
            },
            "required": [],
        },
    },
}


def execute_datetime_tool(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Execute the get_current_datetime tool.

    Args:
        arguments: Optional dict with 'timezone' and 'format' keys.

    Returns:
        Dict containing temporal context based on requested format.
    """
    arguments = arguments or {}
    timezone_str = arguments.get("timezone", "UTC")
    output_format = arguments.get("format", "full")

    try:
        tz = zoneinfo.ZoneInfo(timezone_str)
    except (KeyError, zoneinfo.ZoneInfoNotFoundError):
        tz = zoneinfo.ZoneInfo("UTC")
        timezone_str = "UTC"

    now = datetime.now(tz)

    # Build full result
    full_result = {
        "datetime_iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "day_of_week_short": now.strftime("%a"),
        "hour": now.hour,
        "minute": now.minute,
        "second": now.second,
        "timezone": timezone_str,
        "timezone_offset": now.strftime("%z"),
        "unix_timestamp": int(now.timestamp()),
        "is_weekend": now.weekday() >= 5,
        "week_number": now.isocalendar()[1],
        "day_of_year": now.timetuple().tm_yday,
    }

    # Return based on format
    if output_format == "date_only":
        return {
            "date": full_result["date"],
            "day_of_week": full_result["day_of_week"],
            "is_weekend": full_result["is_weekend"],
            "week_number": full_result["week_number"],
            "day_of_year": full_result["day_of_year"],
            "timezone": full_result["timezone"],
        }
    elif output_format == "time_only":
        return {
            "time": full_result["time"],
            "hour": full_result["hour"],
            "minute": full_result["minute"],
            "second": full_result["second"],
            "timezone": full_result["timezone"],
            "timezone_offset": full_result["timezone_offset"],
        }
    elif output_format == "iso":
        return {
            "datetime_iso": full_result["datetime_iso"],
            "unix_timestamp": full_result["unix_timestamp"],
            "timezone": full_result["timezone"],
        }
    else:  # full
        return full_result


def execute_pray_tool(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Placeholder executor for pray tool.

    The actual executor should be registered by the orchestrator service
    which has access to Telegram credentials.
    """
    arguments = arguments or {}
    message = arguments.get("message", "")

    # Check if an async executor was registered
    if "pray" in ASYNC_TOOL_EXECUTORS:
        # Return a marker that async execution is needed
        return {
            "status": "async_pending",
            "message": message,
            "note": "Message will be sent via async executor",
        }

    logger.warning("pray tool called but no Telegram executor registered")
    return {
        "status": "not_configured",
        "message": message,
        "note": "Telegram executor not configured. Message logged but not sent.",
    }


# Tool executors mapping
TOOL_EXECUTORS: dict[str, Callable] = {
    "get_current_datetime": execute_datetime_tool,
    "pray": execute_pray_tool,
}


def get_tool_definition(tool_name: str) -> dict[str, Any] | None:
    """
    Get the tool definition for a given tool name.

    Args:
        tool_name: Name of the tool (e.g., 'get_current_datetime', 'pray').

    Returns:
        Tool definition dict in OpenAI function calling format, or None if not found.
    """
    builtin_tools = {
        "get_current_datetime": DATETIME_TOOL_DEFINITION,
        "pray": PRAY_TOOL_DEFINITION,
    }
    if tool_name in builtin_tools:
        return builtin_tools[tool_name]
    return TOOL_REGISTRY.get(tool_name, {}).get("definition")


def get_tool_definitions(tool_names: list[str]) -> list[dict[str, Any]]:
    """
    Get tool definitions for a list of tool names.

    Args:
        tool_names: List of tool names to retrieve definitions for.

    Returns:
        List of tool definition dicts.
    """
    definitions = []
    for name in tool_names:
        defn = get_tool_definition(name)
        if defn:
            definitions.append(defn)
    return definitions


def execute_tool(tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Execute a tool by name with given arguments.

    Args:
        tool_name: Name of the tool to execute.
        arguments: Arguments to pass to the tool.

    Returns:
        Tool execution result.

    Raises:
        ValueError: If tool is not found.
    """
    executor = TOOL_EXECUTORS.get(tool_name)
    if executor is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    return executor(arguments)


def register_tool(
    name: str,
    definition: dict[str, Any],
    executor: Callable,
) -> None:
    """
    Register a custom tool.

    Args:
        name: Tool name (must match the function name in definition).
        definition: Tool definition in OpenAI function calling format.
        executor: Callable that executes the tool.
    """
    TOOL_REGISTRY[name] = {"definition": definition}
    TOOL_EXECUTORS[name] = executor


def register_async_tool_executor(name: str, executor: Callable) -> None:
    """
    Register an async executor for a tool.

    This is used for tools that need async execution (e.g., Telegram API calls).
    The async executor will be called by the orchestrator after the LLM returns.

    Args:
        name: Tool name.
        executor: Async callable that executes the tool.
    """
    ASYNC_TOOL_EXECUTORS[name] = executor
    logger.info(f"Registered async executor for tool: {name}")


def get_async_tool_executor(name: str) -> Callable | None:
    """
    Get the async executor for a tool.

    Args:
        name: Tool name.

    Returns:
        Async executor callable or None if not registered.
    """
    return ASYNC_TOOL_EXECUTORS.get(name)
