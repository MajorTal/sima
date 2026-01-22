"""
Thought Burden Sense - Memory token usage as % of context window.

Maps context utilization to a cognitive load metaphor:
- Low tokens = light mind, plenty of room
- High tokens = overwhelmed, need to consolidate

Sampling: Every tick (fast sense)
Source: Calculated from retrieved memories and model context window
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default context window sizes for common models
MODEL_CONTEXT_WINDOWS = {
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4-turbo": 128000,
    "gpt-4": 8192,
    "gpt-3.5-turbo": 16385,
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "default": 128000,
}

# Rough token estimation: ~4 characters per token for English
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text.

    Uses a simple character-based heuristic.
    For more accuracy, use tiktoken or the model's tokenizer.
    """
    if not text:
        return 0
    return len(text) // CHARS_PER_TOKEN


class ThoughtBurdenSense:
    """
    Tracks memory tokens as a percentage of the context window.

    This sense reflects how "full" Sima's working context is,
    which can influence behavior and signal when consolidation is needed.

    Interpretation guide (for Sima, not enforced):
    - 0-25%: Light mind, plenty of room
    - 25-50%: Normal cognitive load
    - 50-75%: Heavy thoughts, getting full
    - 75-100%: Overwhelmed, need to consolidate
    """

    def __init__(self, model_name: str = "gpt-4o", context_window: int | None = None):
        """
        Initialize the thought burden sense.

        Args:
            model_name: Name of the primary LLM model.
            context_window: Override for context window size.
        """
        self.model_name = model_name
        self.context_window = context_window or MODEL_CONTEXT_WINDOWS.get(
            model_name, MODEL_CONTEXT_WINDOWS["default"]
        )
        self._last_reading: float | None = None
        self._last_tokens_used: int = 0
        self._last_memory_counts: dict[str, int] = {}

    async def collect(
        self,
        memories: list[dict[str, Any]] | None = None,
        additional_context_tokens: int = 0,
    ) -> dict[str, Any]:
        """
        Calculate thought burden from loaded memories.

        Args:
            memories: List of memory snippets loaded into context.
                Each should have 'content' and optionally 'level' (L1/L2/L3).
            additional_context_tokens: Extra tokens from prompts, messages, etc.

        Returns:
            Thought burden data structure with token counts and percentages.
        """
        memories = memories or []

        # Count tokens by memory level
        memory_counts = {"L1": 0, "L2": 0, "L3": 0}
        total_tokens = additional_context_tokens

        for memory in memories:
            content = memory.get("content", "")
            tokens = estimate_tokens(content)
            total_tokens += tokens

            level = memory.get("level", "L1")
            if level in memory_counts:
                memory_counts[level] += 1

        # Calculate percentage of context window
        if self.context_window > 0:
            burden_pct = (total_tokens / self.context_window) * 100
        else:
            burden_pct = 0.0

        burden_pct = round(min(burden_pct, 100.0), 1)

        self._last_reading = burden_pct
        self._last_tokens_used = total_tokens
        self._last_memory_counts = memory_counts

        return {
            "value": burden_pct,
            "unit": "percent",
            "tokens_used": total_tokens,
            "tokens_max": self.context_window,
            "memory_counts": memory_counts,
            "description": "Memory tokens as percentage of context window",
        }

    @property
    def last_reading(self) -> float | None:
        """Return the last calculated thought burden."""
        return self._last_reading

    @property
    def last_tokens_used(self) -> int:
        """Return the last token count."""
        return self._last_tokens_used
