FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy workspace files
COPY pyproject.toml ./
COPY packages/ ./packages/
COPY services/api/ ./services/api/

# Install dependencies
RUN uv sync --frozen

# Set working directory for service
WORKDIR /app/services/api

# Expose port
EXPOSE 8001

# Run the application
CMD ["uv", "run", "uvicorn", "sima_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
