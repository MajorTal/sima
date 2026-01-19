# SIMA Sleep Service

Memory consolidation service for SIMA.

## Overview

During "sleep" cycles, this service:
- Compacts recent traces into L1 digests
- Extracts stable semantic memories
- Maintains L3 core memories (genesis.md, stable beliefs)
- Posts sleep telemetry to Telegram

## Memory Tiers

| Level | Content | Retention | Access |
|-------|---------|-----------|--------|
| L0 | Raw event log | Forever | Query via DB |
| L1 | Per-trace digest | 90 days | Retrieved by memory module |
| L2 | Weekly topic maps | 365 days | Retrieved by memory module |
| L3 | Core notes (genesis, stable beliefs) | Forever | **Always available** in context |

## Usage

```bash
# Run once (scheduled job mode)
uv run python -m sima_sleep.main

# Run with custom sleep window
uv run python -m sima_sleep.main --window-hours 12

# Dry run (no persistence)
uv run python -m sima_sleep.main --dry-run
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://localhost/sima` |
| `SLEEP_WINDOW_HOURS` | How far back to look for traces | `24` |
| `MIN_TRACES_FOR_SLEEP` | Minimum traces to trigger consolidation | `1` |
| `TELEGRAM_SLEEP_CHAT_ID` | Telegram channel for sleep telemetry | |
| `TELEGRAM_TELEMETRY_ENABLED` | Enable Telegram posting | `true` |
