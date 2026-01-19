"""
Settings for the sleep consolidation service.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the sleep service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://localhost/sima"

    # AWS
    aws_region: str = "us-east-1"
    aws_profile: str | None = None

    # LLM
    llm_primary_provider: str = "openai"
    llm_primary_model: str = "gpt-4o"
    openai_api_key: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_sleep_chat_id: str = ""
    telegram_conscious_chat_id: str = ""
    telegram_telemetry_enabled: bool = True

    # Sleep parameters
    sleep_window_hours: int = 24  # How far back to look for traces to consolidate
    min_traces_for_sleep: int = 1  # Minimum traces required to run consolidation
    inactivity_threshold_hours: int = 6  # Hours of inactivity before auto-sleep
    max_events_per_batch: int = 100  # Max events to include in a single LLM call

    # Memory tiering
    l1_retention_days: int = 90  # How long to keep L1 (trace digests)
    l2_retention_days: int = 365  # How long to keep L2 (weekly topic maps)
    max_semantic_memories: int = 1000  # Cap on total semantic memories
