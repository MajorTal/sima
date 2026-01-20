FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy workspace files
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/
COPY services/sleep/ ./services/sleep/
COPY docs/ ./docs/
COPY prompts/ ./prompts/

# Install dependencies
RUN uv sync --frozen

# Set working directory for service
WORKDIR /app/services/sleep

# Run the application (sleep job runs once then exits)
CMD ["uv", "run", "python", "-m", "sima_sleep.main"]
