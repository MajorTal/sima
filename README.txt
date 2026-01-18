SIMA — Telegram-Embodied Workspace Agent (AWS/ECS) with Full Cognitive Telemetry
===============================================================================

Overview
--------
Sima is a Telegram-based research agent engineered to instantiate and instrument
theory-derived architectural indicators associated with:

- Recurrent Processing Theory (RPT)
- Global Workspace Theory (GWT)
- Computational Higher-Order Theories (HOT)
- Attention Schema Theory (AST)

Sima is NOT a chatbot wrapper. It is a modular, event-sourced system where:
- “Awake” operation runs a workspace-centric cognitive loop
- Parallel specialist modules produce candidate contents ("subconscious")
- A bottleneck gate selects a limited workspace ("conscious stream")
- A workspace integrator broadcasts the selected contents to modules
- A higher-order monitor produces metacognitive reports
- An attention schema module tracks and predicts attention allocation
- A “sleep” job consolidates the day’s traces into structured memory artifacts

Sima talks to the outside world ONLY through Telegram.
Sima’s internal telemetry is sent to separate Telegram channels (write-only).
Everything is logged to a database and viewable/searchable via a website.

Repository Layout (Exact)
-------------------------
repo/
  README.txt
  plan.md
  LICENSE
  docker-compose.yml
  .env.example

  infra/
    terraform/
      README.md
      envs/
        dev/
          main.tf
          variables.tf
          outputs.tf
        prod/
          main.tf
          variables.tf
          outputs.tf
      modules/
        vpc/
          main.tf
          variables.tf
          outputs.tf
        ecs/
          main.tf
          variables.tf
          outputs.tf
        rds/
          main.tf
          variables.tf
          outputs.tf
        s3/
          main.tf
          variables.tf
          outputs.tf
        secrets/
          main.tf
          variables.tf
          outputs.tf

  services/
    ingest-api/
      Dockerfile
      pyproject.toml
      sima_ingest/
        __init__.py
        main.py
        routes.py
        settings.py

    orchestrator/
      Dockerfile
      pyproject.toml
      sima_orchestrator/
        __init__.py
        worker.py
        awake_loop.py
        module_runner.py
        telegram_out.py
        redaction.py
        settings.py

    sleep/
      Dockerfile
      pyproject.toml
      sima_sleep/
        __init__.py
        job.py
        consolidation.py
        settings.py

    api/
      Dockerfile
      pyproject.toml
      sima_api/
        __init__.py
        main.py
        auth.py
        routes_public.py
        routes_lab.py
        db.py
        search.py
        settings.py

    web/
      Dockerfile
      package.json
      next.config.js
      app/
        (public)/
          layout.tsx
          page.tsx
          traces/
            [traceId]/
              page.tsx
          search/
            page.tsx
        (lab)/
          layout.tsx
          page.tsx
          traces/
            [traceId]/
              page.tsx
          events/
            [eventId]/
              page.tsx
          dashboards/
            indicators/
              page.tsx
            models/
              page.tsx
          admin/
            redaction/
              page.tsx
      components/
        TraceTimeline.tsx
        EventGraph.tsx
        FiltersPanel.tsx
        IndicatorCards.tsx
      lib/
        api.ts
        types.ts
        auth.ts
      styles/
        globals.css

  packages/
    sima-core/
      pyproject.toml
      sima_core/
        __init__.py
        types.py
        events.py
        ids.py
        time.py

    sima-storage/
      pyproject.toml
      sima_storage/
        __init__.py
        db.py
        models.py
        migrations/
          alembic.ini
          env.py
          versions/
            0001_init.py
        s3.py

    sima-llm/
      pyproject.toml
      sima_llm/
        __init__.py
        router.py
        providers/
          __init__.py
          openai.py
          google.py
          xai.py
          bedrock.py
        schemas.py
        tracing.py

    sima-prompts/
      pyproject.toml
      sima_prompts/
        __init__.py
        registry.py
        renderer.py
      prompts/
        shared/
          style.md
          safety.md
          schemas/
            percept.schema.json
            candidates.schema.json
            workspace.schema.json
            metacog.schema.json
            attention_gate.schema.json
            attention_schema.schema.json
            sleep_digest.schema.json
            message.schema.json
        modules/
          perception_rpt.yaml
          memory_retrieval.yaml
          planner.yaml
          critic.yaml
          attention_gate.yaml
          workspace_integrator.yaml
          metacog_hot.yaml
          attention_schema_ast.yaml
          speaker.yaml
          sleep_consolidation.yaml

  docs/
    architecture/
      overview.md
      event_model.md
      aws_deployment.md
      telemetry.md
    website/
      public.md
      lab.md
    ctests/
      indicator_mapping.md
      probe_specs.md
    prompts/
      prompt_design.md

  scripts/
    dev_up.sh
    dev_down.sh
    seed_demo_trace.py
    export_trace.py

  tests/
    test_event_store.py
    test_prompt_schemas.py
    test_awake_loop.py


Quick Start (Local)
-------------------
Prerequisites:
- Docker + Docker Compose
- Python 3.11+
- Node 20+ (for web)
- A Telegram bot token (BotFather)
- Telegram chat IDs for:
  (1) external chat, (2) conscious channel, (3) subconscious channel, (optional) sleep channel

1) Copy env template:
   cp .env.example .env

2) Start dependencies:
   docker compose up -d postgres

3) Run migrations:
   cd packages/sima-storage
   pip install -e .
   alembic upgrade head

4) Start services (dev):
   ./scripts/dev_up.sh

5) Start web:
   cd services/web
   npm install
   npm run dev

Telegram Setup
--------------
- Create bot via BotFather -> get TELEGRAM_BOT_TOKEN
- Create a private channel for conscious stream, add bot as admin, get chat ID
- Create a private channel for subconscious stream, add bot as admin, get chat ID
- Optionally create a private channel for sleep stream
- External chat: DM the bot or add to a group; record chat ID

Environment Variables (Minimal)
-------------------------------
Core:
- TELEGRAM_BOT_TOKEN=...
- TELEGRAM_EXTERNAL_CHAT_ID=...
- TELEGRAM_CONSCIOUS_CHAT_ID=...
- TELEGRAM_SUBCONSCIOUS_CHAT_ID=...
- TELEGRAM_SLEEP_CHAT_ID=... (optional)

Storage:
- DATABASE_URL=postgresql+psycopg://...
- S3_BUCKET=... (optional for large payloads)
- AWS_REGION=...

Queues (AWS deploy):
- SQS_INCOMING_URL=...

LLMs:
- LLM_PRIMARY_PROVIDER=openai|google|xai|bedrock
- LLM_PRIMARY_MODEL=...
- LLM_FAST_PROVIDER=...
- LLM_FAST_MODEL=...
- LLM_SLEEP_PROVIDER=...
- LLM_SLEEP_MODEL=...

Behavior:
- WORKSPACE_CAPACITY_K=7
- RECURRENCE_STEPS=3
- AUTONOMOUS_TICK_ENABLED=true|false
- AUTONOMOUS_TICK_CRON=rate(10 minutes)
- REDACTION_MODE=off|public_safe

AWS Deployment (ECS/Fargate)
----------------------------
Terraform in infra/terraform creates:
- VPC + subnets
- ECS cluster + services:
  - sima-ingest-api (ALB webhook)
  - sima-orchestrator (SQS consumer)
  - sima-api (web backend)
  - sima-web (frontend)
  - sima-sleep (scheduled task via EventBridge)
- RDS Postgres
- S3 bucket for large payloads
- Secrets Manager entries for tokens/keys

High-Level Data Flow
--------------------
Telegram -> (Webhook) ingest-api -> SQS -> orchestrator
orchestrator:
- runs awake loop (modules -> attention gate -> workspace -> broadcast -> speaker)
- sends Telegram outbound messages (external + conscious + subconscious)
- persists every event (event sourcing) to Postgres (+ optional S3)

Nightly:
EventBridge -> sleep task -> loads prior events -> writes digest + memory updates


Where to Look Next
------------------
- plan.md: full engineering plan and milestones
- docs/architecture/: system design docs
- docs/website/: UI specifications (public + lab)
- packages/sima-prompts/prompts/: module prompts + JSON schemas

License
-------
See LICENSE.
