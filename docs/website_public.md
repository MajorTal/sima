# Public Website Spec (General Audience)

## Goals
- Make Sima understandable without exposing raw internal telemetry.
- Provide safe browsing/search/sharing of selected traces.

## Information Architecture
- Home
- Explore (public traces)
- Trace detail
- Search
- About / FAQ (short, technical, non-philosophical)

## Home
- What Sima is (1–2 paragraphs)
- Live feed (external messages + optional high-level “conscious stream” summaries)
- Featured traces

## Explore
- Cards: topic, date, excerpt, tags
- Filters: date range, tags

## Trace Detail
- External transcript
- "Research note" panel:
  - compact workspace summary (no raw JSON)
  - indicators (high-level: “recurrence present”, “workspace bottleneck active”)
- Share link

## Search
- Full-text search across public traces
- Filters: tag, date

## Redaction
- Always remove secrets and infrastructure identifiers.
- Remove raw prompts.
- Remove raw module JSON.
- Allow only curated high-level internal summaries.

## Performance
- SSR for trace pages
- Pagination for explore/search
