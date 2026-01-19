#!/bin/bash
# Start local development environment for SIMA

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo "=== Starting SIMA Development Environment ==="

# Check for required tools
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "uv is required but not installed. Install with: pip install uv" >&2; exit 1; }

# Start infrastructure
echo ""
echo "Starting PostgreSQL and LocalStack..."
docker compose up -d postgres localstack

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until docker compose exec -T postgres pg_isready -U sima -d sima >/dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready!"

# Wait for LocalStack to be ready
echo "Waiting for LocalStack..."
sleep 5
echo "LocalStack should be ready!"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
uv sync

# Run migrations
echo ""
echo "Running database migrations..."
cd packages/sima-storage
uv run alembic upgrade head
cd "$ROOT_DIR"

echo ""
echo "=== Development Environment Ready ==="
echo ""
echo "Infrastructure:"
echo "  - PostgreSQL: localhost:5432 (user: sima, password: sima_dev, db: sima)"
echo "  - LocalStack: localhost:4566"
echo ""
echo "To start services, run in separate terminals:"
echo "  - Ingest API:   cd services/ingest-api && uv run uvicorn sima_ingest.main:app --reload --port 8000"
echo "  - Backend API:  cd services/api && uv run uvicorn sima_api.main:app --reload --port 8001"
echo "  - Orchestrator: cd services/orchestrator && uv run python -m sima_orchestrator.worker"
echo "  - Web Frontend: cd services/web && npm install && npm run dev"
echo ""
echo "Or use the seed script to add demo data:"
echo "  python scripts/seed_demo_trace.py"
