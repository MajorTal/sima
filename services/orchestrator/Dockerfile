FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy workspace files
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/
COPY services/orchestrator/ ./services/orchestrator/

# Install dependencies
RUN uv sync --frozen

# Set working directory for service
WORKDIR /app/services/orchestrator

# Run the application
CMD ["uv", "run", "python", "-m", "sima_orchestrator.worker"]
