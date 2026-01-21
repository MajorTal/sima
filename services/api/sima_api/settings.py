"""
Configuration settings for the API service.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API settings loaded from environment."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    # Database
    database_url: str = "postgresql+asyncpg://sima:sima_dev@localhost:5432/sima"

    # Service
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False

    # Auth
    lab_password: str = ""  # If empty, lab routes are unprotected
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # Admin auth (for system reset)
    admin_username: str = "tal"
    admin_password: str = "cTw1971r"

    # CORS
    cors_origins: str = "*"

    # AWS / SQS (for triggering ticks and webhook)
    aws_region: str = "us-east-1"
    aws_profile: str | None = None
    sqs_queue_url: str = "http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/sima-ingest"
    sqs_endpoint_url: str | None = "http://localhost:4566"  # For LocalStack; set to None for real AWS

    # Telegram (for webhook)
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""  # Optional webhook secret for verification


settings = Settings()
