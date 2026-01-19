"""
Shared pytest fixtures for SIMA tests.
"""

import os
import pytest
from pathlib import Path


# Ensure we're using test environment
os.environ.setdefault("TESTING", "true")


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def env_file(project_root: Path) -> Path:
    """Get path to .env file."""
    return project_root / ".env"


@pytest.fixture(scope="session")
def load_env(env_file: Path):
    """Load environment variables from .env file."""
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


@pytest.fixture
def openai_api_key(load_env) -> str | None:
    """Get OpenAI API key from environment."""
    return os.environ.get("OPENAI_API_KEY")


@pytest.fixture(scope="session")
def database_url(load_env) -> str:
    """Get database URL from environment."""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://sima:sima_dev@localhost:5432/sima"
    )


@pytest.fixture
def sqs_queue_url(load_env) -> str:
    """Get SQS queue URL from environment."""
    return os.environ.get(
        "SQS_QUEUE_URL",
        "http://localhost:4566/000000000000/sima-ingest-queue"
    )


@pytest.fixture
def aws_endpoint_url(load_env) -> str | None:
    """Get AWS endpoint URL (for LocalStack)."""
    return os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
