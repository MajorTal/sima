FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy workspace files
COPY pyproject.toml ./
COPY packages/ ./packages/
COPY services/ingest-api/ ./services/ingest-api/

# Install dependencies
RUN uv sync --frozen

# Set working directory for service
WORKDIR /app/services/ingest-api

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "sima_ingest.main:app", "--host", "0.0.0.0", "--port", "8000"]
