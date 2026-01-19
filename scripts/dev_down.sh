#!/bin/bash
# Stop local development environment for SIMA

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo "=== Stopping SIMA Development Environment ==="

# Stop containers
docker compose down

echo ""
echo "Development environment stopped."
echo "Data is preserved in Docker volumes."
echo ""
echo "To remove all data, run:"
echo "  docker compose down -v"
