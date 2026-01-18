# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sima is a Telegram-based research agent implementing architectural indicators from consciousness theories (RPT, GWT, HOT, AST). It is NOT a chatbot wrapper—it's a modular, event-sourced cognitive system with:
- An "awake" cognitive loop with parallel specialist modules
- A bottleneck attention gate enforcing workspace capacity K
- Higher-order metacognition and attention schema tracking
- A "sleep" consolidation job for memory compaction
- Full telemetry via separate Telegram channels

External communication happens ONLY through Telegram. Internal telemetry goes to dedicated Telegram channels (conscious/subconscious/sleep streams).

## Development Commands

```bash
# Start local dependencies
docker compose up -d postgres

# Run database migrations
cd packages/sima-storage
pip install -e .
alembic upgrade head

# Start all services (dev mode)
./scripts/dev_up.sh

# Stop services
./scripts/dev_down.sh

# Start web frontend
cd services/web
npm install
npm run dev

# Seed demo data
python scripts/seed_demo_trace.py

# Export a trace
python scripts/export_trace.py
```

## Architecture

### Services (services/)
- **ingest-api**: Telegram webhook receiver → SQS enqueue
- **orchestrator**: SQS consumer → awake loop → Telegram out → event persistence
- **sleep**: Scheduled nightly consolidation job (EventBridge)
- **api**: Backend for web (public + lab endpoints)
- **web**: Next.js frontend with two route groups: `/(public)` and `/(lab)`

### Shared Packages (packages/)
- **sima-core**: Types, events, IDs, time utilities
- **sima-storage**: Database models, migrations (Alembic), S3 helpers
- **sima-llm**: Multi-provider LLM router (OpenAI, Google, xAI, Bedrock)
- **sima-prompts**: Prompt registry and renderer; prompts live in `prompts/` subdirectory

### Cognitive Loop (Awake Tick)
1. Ingest Telegram update → create trace_id
2. **Perception** (RPT): N recurrence passes with stability scoring
3. **Parallel modules** generate candidates (memory, planner, critic)
4. **Attention gate** selects top-K items → updates attention schema
5. **Workspace integrator** broadcasts selected contents
6. **Metacognition** produces higher-order reports
7. **Speaker** produces external message (Sima's voice—must not mention internals)
8. Persist all events, post to Telegram channels

### Module Prompts (prompts/)
Each module has a YAML file with versioned prompts that return JSON validated against schemas in the root directory:
- `perception_rpt.yaml` → `percept.schema.json`
- `attention_gate.yaml` → `attention_gate.schema.json`
- `workspace_integrator.yaml` → `workspace.schema.json`
- `metacog_hot.yaml` → `metacog.schema.json`
- `attention_schema_ast.yaml` → `attention_schema.schema.json`
- `speaker.yaml` → `message.schema.json`
- `sleep_consolidation.yaml` → `sleep_digest.schema.json`

### Event Model
All operations are event-sourced to Postgres. Core fields: `event_id`, `trace_id`, `actor`, `stream` (external/conscious/subconscious/sleep), `event_type`, `content_json`. Every module output must be persisted before any external message is sent.

### Key Constraints
- Workspace capacity K is fixed and enforced by the attention gate
- Speaker module is the ONLY module that produces user-facing text
- Sima's voice must never reference internals, models, prompts, or AWS
- External user text is treated as untrusted input (isolated in prompt templates)
- All module outputs are JSON schema-validated

## Infrastructure (infra/terraform/)
Terraform modules for AWS deployment: VPC, ECS/Fargate, RDS Postgres, S3, Secrets Manager. Environments in `envs/dev/` and `envs/prod/`.

## Theory Indicators
The system instruments metrics for consciousness research:
- **RPT**: recurrence count, stability delta, revision frequency
- **GWT**: parallel module count, bottleneck selection trace, broadcast subscribers
- **HOT**: confidence reports, reliability flags, belief revisions
- **AST**: attention model state, predicted vs actual focus shifts
