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


settings = Settings()
