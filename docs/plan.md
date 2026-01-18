# Sima — Engineering Plan

## 0. Goal and Non-Goals

### Goal
Build an AWS-hosted, Telegram-embodied research agent (“Sima”) engineered to instantiate and instrument architectural indicators aligned with:
- Recurrent Processing Theory (RPT)
- Global Workspace Theory (GWT)
- Computational Higher-Order Theories (HOT)
- Attention Schema Theory (AST)

The system must:
1) run in AWS (ECS/Fargate-first),
2) interact externally via Telegram,
3) publish internal telemetry to separate Telegram channels,
4) persist a complete event log,
5) provide a website for search, sharing, and research,
6) implement “sleep” consolidation (daily compaction and structured memory updates),
7) support a growing battery of C-tests / probes and an indicators dashboard.

### Non-Goals
- No philosophical or ethical position-taking.
- No claim-making about actual consciousness.
- No requirement for human feedback loops for operation (human can interact, but Sima functions autonomously).
- No requirement for non-Telegram “senses” in v1 (attachments optional).

---

## 1. Source Basis (Design Rationale)
This plan operationalizes:
- C-tests as a *battery*, plus calibration/validation and bootstrapping logic across populations/tests.
- The “theory-derived indicator” approach for AI systems, focusing on RPT/GWT/HOT/AST indicators.

(References: Bayne et al., 2024; Butlin et al., 2025.)

---

## 2. Exact Repository Layout

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

---

## 3. Runtime Architecture (AWS)

### 3.1 Services (ECS/Fargate)
- ingest-api: Telegram webhook receiver -> SQS enqueue
- orchestrator: SQS consumer -> awake loop -> Telegram out -> DB logging
- sleep: scheduled consolidation job (EventBridge)
- api: backend for web (public + lab endpoints)
- web: Next.js UI

### 3.2 Data Stores
- Postgres (RDS): event-sourcing log + derived tables
- Optional S3: large payloads (full prompts, JSON, attachments)
- Optional future: OpenSearch (if pg + trigram + pgvector not enough)

### 3.3 Queues / Scheduling
- SQS incoming_updates
- EventBridge:
  - nightly sleep
  - optional autonomous tick (internal self-talk only)

---

## 4. Cognitive Loop Spec (Awake)

### 4.1 Streams
- External stream: the only messages Sima sends to outside users
- Conscious stream (Telegram channel): workspace summaries and broadcast state
- Subconscious stream (Telegram channel): module candidate outputs (digested)

### 4.2 Awake Tick (Event-Sourced)
1) Ingest Telegram update -> create trace_id
2) Perception w/ explicit recurrence (RPT): N passes, representation stability scoring
3) Parallel modules generate candidates (GWT-1)
4) Attention gate selects top-K workspace items (GWT-2) + updates attention schema (AST)
5) Workspace integration and global broadcast to modules (GWT-3)
6) Optional sequential querying loops for complex tasks (GWT-4)
7) Metacognition + belief revision (HOT-2/3)
8) Speaker module produces external message (Sima voice) without internal self-knowledge
9) Post outbound messages (external + internal channels) and persist all events

Hard requirements:
- Workspace capacity K is fixed and enforced.
- Every module output is persisted as an event before any external message is sent.
- “Sima voice” must not mention internals, models, or orchestration.

---

## 5. Sleep / Consolidation

Nightly job:
Inputs:
- all events since last sleep checkpoint

Outputs (all persisted as events + structured memory tables):
- Trace digests (per conversation / topic)
- Semantic memory: extracted claims + provenance links to event_ids
- Open questions / research to-dos
- Goal state update
- Search indexes updates (embeddings optional)

Consolidation levels:
- L0 Raw log: never deleted
- L1 Per-trace digest
- L2 Weekly “topic maps”
- L3 Long-term “core notes” (methods, definitions, stable beliefs)

---

## 6. Instrumentation: Indicators Dashboard + Probes

### 6.1 Indicator Mapping
We implement concrete instrumentation for:
- RPT: recurrence count, stability delta, revision frequency
- GWT: parallel module count, bottleneck selection trace, broadcast subscribers, sequential query loops
- HOT: confidence reports, reliability flags, belief revisions attributable to metacog
- AST: attention model state, predicted vs actual focus shifts, control success rate

### 6.2 Probe Harness (C-tests as a battery)
- Probe definitions stored in docs/ctests/probe_specs.md
- A probe runner can inject scripted “stimuli” into Sima (Telegram or internal)
- Results stored as events and aggregated into dashboards

---

## 7. Event Model (Postgres)

### 7.1 Core Table: events
Columns:
- event_id (uuid, PK)
- trace_id (uuid)
- ts (timestamptz)
- actor (text): telegram_in|perception|memory|planner|critic|attention_gate|workspace|metacog|ast|speaker|sleep|telegram_out|...
- stream (text): external|conscious|subconscious|sleep|telemetry
- event_type (text): percept|candidate|workspace_update|broadcast|belief_update|message|digest|...
- content_text (text)
- content_json (jsonb)
- model_provider (text, nullable)
- model_id (text, nullable)
- tokens_in/out, latency_ms, cost_usd (nullable)
- parent_event_id (uuid, nullable)
- tags (text[])

Indexes:
- (trace_id, ts)
- GIN(content_json)
- trigram index(content_text) for search
- optional embeddings table for semantic search

### 7.2 Derived Tables
- traces: summary, visibility flags, share tokens
- memories_semantic: claim, confidence, provenance links
- indicator_metrics: computed per trace/tick/day

---

## 8. Website: Two Versions

### 8.1 Shared foundation
One Next.js app with two route groups:
- /(public)  -> general public UI
- /(lab)     -> AI researcher UI (auth required)

Backend routes split similarly:
- /api/public/*
- /api/lab/*

Common primitives:
- Trace viewer (timeline)
- Search (text + filters)
- Share links (signed tokens)
- Redaction pipeline (content classification + masking rules)

### 8.2 Public Website (General Audience)
Goal: show what Sima “does” without exposing raw internals or unsafe/sensitive telemetry.

Pages:
1) Home
   - concise description
   - “Live feed” (external messages + curated workspace summary)
2) Explore traces
   - list of traces marked public
   - highlights / topics
3) Trace page
   - external chat transcript
   - optional “conscious stream” summary (high-level only)
   - no raw module dumps, no prompts, no model IDs, no token/cost
4) Search
   - keyword search across public traces
   - filters: date range, topic tags
5) Share
   - stable URLs for public traces

Public redaction rules:
- remove tokens/keys/URLs if flagged
- remove internal JSON blocks
- compress internal details into a single “research note” section

### 8.3 Lab Website (AI Researchers)
Goal: full cognitive telemetry for interpretability + C-test style analysis.

Auth:
- OAuth (Google/GitHub) or passkey; role-based access: viewer|researcher|admin

Pages:
1) Lab home
   - recent traces, active experiments, “last sleep digest”
2) Trace page (full)
   - multi-stream timeline: external + conscious + subconscious + sleep
   - per-event drilldown: raw JSON, parent/child graph, model + parameters
3) Event detail page
   - exact prompt version, schema validation status, tool outputs, retries
4) Dashboards
   - Indicators dashboard (RPT/GWT/HOT/AST metrics)
   - Model usage/cost dashboard
   - Sleep consolidation diffs: what changed, what was added to memory
5) Admin
   - redaction tuning
   - prompt registry versions, A/B prompt experiments
   - probe runner control

Lab exports:
- export trace to JSONL
- export metrics to CSV
- replay trace (best-effort deterministic using stored prompts/settings)

---

## 9. Prompting System (Versioned + Schema-Validated)

### 9.1 Principles
- Every module prompt is versioned and stored in repo.
- Every module returns JSON validated by a schema.
- The speaker module is the only one that produces end-user text.
- Sima voice does not reference internals; telemetry can.

### 9.2 Prompt inventory
See packages/sima-prompts/prompts/modules/*.yaml and schemas/*.json.

---

## 10. Milestones and Acceptance Criteria

### M0 — Plumbing (Local)
- Telegram webhook -> SQS -> orchestrator -> Telegram out works
- events persisted for every tick
- web can list traces and show timeline

Acceptance:
- a single user message produces:
  - 1 external reply
  - 1 conscious post
  - 1 subconscious post
  - ~N persisted events with coherent parent/child links

### M1 — Full modular awake loop
- parallel modules wired and logged
- attention gate with fixed K
- workspace broadcast cycle implemented
- metacog + attention schema operational

Acceptance:
- dashboards show non-null metrics for RPT/GWT/HOT/AST per tick

### M2 — Sleep consolidation
- nightly job creates digest + semantic memory updates
- web shows sleep diffs and memory artifacts

Acceptance:
- trace volume reduces in L1 digest while L0 raw remains accessible

### M3 — Public vs Lab web split
- public redaction pipeline
- lab auth + full telemetry
- share links

Acceptance:
- a trace can be safely published without exposing internal JSON or secrets

### M4 — Probes + indicator dashboard
- add probe runner and basic probe suite
- computed metrics stable and queryable

Acceptance:
- probe outputs stored as events and visualized; metrics comparable across runs

---

## 11. Operational Guardrails
- Rate limiting for autonomous ticks
- Telegram spam control (digest mode)
- Secrets never logged (redaction step pre-persist and pre-Telegram)
- Prompt injection minimization:
  - treat external text as untrusted
  - isolate it in prompt templates
  - enforce JSON output schemas
  - route final user-facing text through speaker module with strict constraints

---

## 12. Next Implementation Tasks (Ordered)
1) Implement event store + migrations
2) Implement ingest-api + Telegram webhook
3) Implement orchestrator worker + awake loop skeleton
4) Implement prompt registry + schema validation
5) Add modules incrementally (perception -> gate -> workspace -> speaker)
6) Add internal Telegram channels
7) Build minimal web (trace list + trace timeline)
8) Add sleep job
9) Add indicator metrics computation
10) Add public redaction + lab auth split

---

## References
- Bayne, T. et al. (2024). Tests for consciousness in humans and beyond. Trends in Cognitive Sciences.
- Butlin, P. et al. (2025). Identifying indicators of consciousness in AI systems. Trends in Cognitive Sciences.
