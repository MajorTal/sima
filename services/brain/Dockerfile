FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy workspace files
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/
COPY services/brain/ ./services/brain/
COPY prompts/ ./prompts/

# Install dependencies
RUN uv sync --frozen

# Set working directory for service
WORKDIR /app/services/brain

# Run the application
CMD ["uv", "run", "python", "-m", "sima_brain.worker"]
