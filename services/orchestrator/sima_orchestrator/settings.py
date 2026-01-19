"""
Settings for the orchestrator service.
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Configuration settings for the orchestrator."""

    # AWS
    aws_region: str = field(default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1"))
    sqs_incoming_url: str = field(default_factory=lambda: os.environ.get("SQS_INCOMING_URL", ""))

    # Telegram
    telegram_bot_token: str = field(
        default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN", "")
    )
    telegram_external_chat_id: str = field(
        default_factory=lambda: os.environ.get("TELEGRAM_EXTERNAL_CHAT_ID", "")
    )
    telegram_conscious_chat_id: str = field(
        default_factory=lambda: os.environ.get("TELEGRAM_CONSCIOUS_CHAT_ID", "")
    )
    telegram_subconscious_chat_id: str = field(
        default_factory=lambda: os.environ.get("TELEGRAM_SUBCONSCIOUS_CHAT_ID", "")
    )

    # LLM
    llm_primary_provider: str = field(
        default_factory=lambda: os.environ.get("LLM_PRIMARY_PROVIDER", "openai")
    )
    llm_primary_model: str = field(
        default_factory=lambda: os.environ.get("LLM_PRIMARY_MODEL", "gpt-4o")
    )
    llm_fast_provider: str = field(
        default_factory=lambda: os.environ.get("LLM_FAST_PROVIDER", "openai")
    )
    llm_fast_model: str = field(
        default_factory=lambda: os.environ.get("LLM_FAST_MODEL", "gpt-4o-mini")
    )

    # Cognitive parameters
    recurrence_steps: int = field(
        default_factory=lambda: int(os.environ.get("RECURRENCE_STEPS", "3"))
    )
    workspace_capacity: int = field(
        default_factory=lambda: int(os.environ.get("WORKSPACE_CAPACITY_K", "7"))
    )
    competition_iterations: int = field(
        default_factory=lambda: int(os.environ.get("COMPETITION_ITERATIONS", "10"))
    )
    belief_revision_threshold: float = field(
        default_factory=lambda: float(os.environ.get("BELIEF_REVISION_THRESHOLD", "0.4"))
    )
    max_belief_revision_iterations: int = field(
        default_factory=lambda: int(os.environ.get("MAX_BELIEF_REVISION_ITERATIONS", "2"))
    )

    # Time-sensing
    minute_tick_enabled: bool = field(
        default_factory=lambda: os.environ.get("MINUTE_TICK_ENABLED", "false").lower() == "true"
    )
    autonomous_tick_enabled: bool = field(
        default_factory=lambda: os.environ.get("AUTONOMOUS_TICK_ENABLED", "false").lower()
        == "true"
    )
    timezone: str = field(default_factory=lambda: os.environ.get("TIMEZONE", "UTC"))

    # Telegram telemetry
    telegram_telemetry_enabled: bool = field(
        default_factory=lambda: os.environ.get("TELEGRAM_TELEMETRY_ENABLED", "true").lower() == "true"
    )

    # Database
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL", "postgresql+psycopg://localhost/sima"
        )
    )
