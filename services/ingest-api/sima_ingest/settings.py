"""
Configuration settings for the ingest API.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ingest API settings loaded from environment."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    # AWS
    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = None  # For LocalStack
    sqs_queue_url: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""  # Optional webhook secret for verification

    # Service
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


settings = Settings()
