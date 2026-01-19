"""
Settings for the orchestrator service.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the orchestrator."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # AWS
    aws_region: str = "us-east-1"
    aws_profile: str | None = None
    sqs_queue_url: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_external_chat_id: str = ""
    telegram_conscious_chat_id: str = ""
    telegram_subconscious_chat_id: str = ""
    telegram_tal_chat_id: int = 1196325805  # Tal's chat ID for prayer tool

    # LLM
    llm_primary_provider: str = "openai"
    llm_primary_model: str = "gpt-4o"
    llm_fast_provider: str = "openai"
    llm_fast_model: str = "gpt-4o-mini"
    openai_api_key: str = ""

    # Cognitive parameters
    recurrence_steps: int = 3
    workspace_capacity: int = 7
    competition_iterations: int = 10
    belief_revision_threshold: float = 0.4
    max_belief_revision_iterations: int = 2

    # Time-sensing
    minute_tick_enabled: bool = False
    autonomous_tick_enabled: bool = False
    timezone: str = "UTC"

    # Telegram telemetry
    telegram_telemetry_enabled: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://localhost/sima"
