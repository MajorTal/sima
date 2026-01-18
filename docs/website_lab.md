# Lab Website Spec (AI Researchers)

## Goals
- Full cognitive telemetry: module outputs, schemas, prompts, and event graphs.
- Reproducible research workflows: export, replay, probes, dashboards.

## AuthN/AuthZ
- OAuth (Google/GitHub)
- Roles: viewer, researcher, admin
- Trace visibility flags: private, lab, public

## Pages
1) Lab Home
   - recent traces
   - latest sleep digest
   - ongoing probe runs

2) Trace Viewer (Full)
   - multi-stream timeline: external / conscious / subconscious / sleep
   - per-event drilldown: JSON, prompt version, model, tokens, cost, latency
   - parent/child event graph
   - “workspace frames” view: show selected items and why

3) Event Detail
   - exact prompt payload and response
   - schema validation
   - retries and fallbacks

4) Dashboards
   - Indicators: RPT/GWT/HOT/AST metrics over time
   - Model usage/cost and error rates
   - Sleep effects: diffs on memory (added/revised/retracted)

5) Admin
   - redaction controls
   - prompt registry: version pinning, A/B tests
   - probe runner configuration

## Exports
- Trace export: JSONL (events ordered)
- Metrics export: CSV
- Replay: best-effort deterministic run (same prompts/settings)

## Research UX Details
- Filters:
  - actor/module
  - event type
  - stream
  - confidence thresholds
- Compare mode:
  - side-by-side traces for the same probe with different prompt versions
