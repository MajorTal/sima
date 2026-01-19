"""
Core type definitions for SIMA.
"""

from enum import Enum


class Stream(str, Enum):
    """Output streams for events."""
    EXTERNAL = "external"          # User-facing Telegram messages
    CONSCIOUS = "conscious"        # Inner monologue, workspace state
    SUBCONSCIOUS = "subconscious"  # Module outputs (full JSON)
    SLEEP = "sleep"                # Consolidation reports


class Actor(str, Enum):
    """Module/component that produced an event."""
    TELEGRAM_IN = "telegram_in"
    PERCEPTION = "perception"
    MEMORY = "memory"
    PLANNER = "planner"
    CRITIC = "critic"
    ATTENTION_GATE = "attention_gate"
    WORKSPACE = "workspace"
    METACOG = "metacog"
    AST = "ast"  # Attention Schema
    SPEAKER = "speaker"
    MONOLOGUE = "monologue"
    SLEEP = "sleep"
    TELEGRAM_OUT = "telegram_out"
    SYSTEM = "system"


class EventType(str, Enum):
    """Types of events in the system."""
    # Input events
    MESSAGE_IN = "message_in"
    TICK = "tick"

    # Cognitive events
    PERCEPT = "percept"
    CANDIDATE = "candidate"
    SELECTION = "selection"
    WORKSPACE_UPDATE = "workspace_update"
    BROADCAST = "broadcast"
    METACOG_REPORT = "metacog_report"
    BELIEF_REVISION = "belief_revision"
    ATTENTION_PREDICTION = "attention_prediction"
    ATTENTION_COMPARISON = "attention_comparison"

    # Output events
    MONOLOGUE = "monologue"
    MESSAGE_OUT = "message_out"

    # Sleep events
    SLEEP_START = "sleep_start"
    SLEEP_DIGEST = "sleep_digest"
    MEMORY_CONSOLIDATION = "memory_consolidation"
    SLEEP_END = "sleep_end"

    # System events
    ERROR = "error"
    PAUSE = "pause"
    RESUME = "resume"


class InputType(str, Enum):
    """Types of inputs that trigger the awake loop."""
    USER_MESSAGE = "user_message"
    MINUTE_TICK = "minute_tick"
    AUTONOMOUS_TICK = "autonomous_tick"


class TickType(str, Enum):
    """Types of scheduled ticks."""
    MINUTE = "minute"
    AUTONOMOUS = "autonomous"
