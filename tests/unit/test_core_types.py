"""
Unit tests for sima_core types.
"""

import pytest

from sima_core.types import Actor, EventType, InputType, Stream


class TestEnumValues:
    """Test that enum values are lowercase strings."""

    def test_stream_values(self):
        """Stream enum values should be lowercase."""
        assert Stream.EXTERNAL.value == "external"
        assert Stream.CONSCIOUS.value == "conscious"
        assert Stream.SUBCONSCIOUS.value == "subconscious"
        assert Stream.SLEEP.value == "sleep"

    def test_actor_values(self):
        """Actor enum values should be lowercase."""
        assert Actor.TELEGRAM_IN.value == "telegram_in"
        assert Actor.PERCEPTION.value == "perception"
        assert Actor.MEMORY.value == "memory"
        assert Actor.PLANNER.value == "planner"
        assert Actor.CRITIC.value == "critic"
        assert Actor.ATTENTION_GATE.value == "attention_gate"
        assert Actor.WORKSPACE.value == "workspace"
        assert Actor.METACOG.value == "metacog"
        assert Actor.AST.value == "ast"
        assert Actor.SPEAKER.value == "speaker"
        assert Actor.TELEGRAM_OUT.value == "telegram_out"

    def test_event_type_values(self):
        """EventType enum values should be lowercase."""
        assert EventType.MESSAGE_IN.value == "message_in"
        assert EventType.PERCEPT.value == "percept"
        assert EventType.CANDIDATE.value == "candidate"
        assert EventType.SELECTION.value == "selection"
        assert EventType.WORKSPACE_UPDATE.value == "workspace_update"
        assert EventType.METACOG_REPORT.value == "metacog_report"
        assert EventType.MESSAGE_OUT.value == "message_out"

    def test_input_type_values(self):
        """InputType enum values should be lowercase."""
        assert InputType.USER_MESSAGE.value == "user_message"
        assert InputType.MINUTE_TICK.value == "minute_tick"
        assert InputType.AUTONOMOUS_TICK.value == "autonomous_tick"


class TestEnumStringConversion:
    """Test enum to string conversion."""

    def test_stream_str(self):
        """Stream should convert to its value when used as string."""
        assert str(Stream.EXTERNAL) == "Stream.EXTERNAL"
        assert Stream.EXTERNAL.value == "external"

    def test_enum_is_str_subclass(self):
        """All enums should be str subclasses for JSON serialization."""
        assert isinstance(Stream.EXTERNAL, str)
        assert isinstance(Actor.PERCEPTION, str)
        assert isinstance(EventType.PERCEPT, str)
        assert isinstance(InputType.USER_MESSAGE, str)
