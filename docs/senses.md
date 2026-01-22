# Sima Senses — Specification

> **Status**: Draft
> **Author**: Tal + Claude
> **Date**: 2026-01-22

## Overview

Sima's current sensory input is limited to Telegram messages and time-based ticks. This spec adds **interoceptive senses** (internal body-state awareness) and **environmental senses** (external world awareness) to create a richer, more continuous perceptual experience.

### Design Principles

1. **Just data** — Senses provide raw values. Sima interprets their meaning.
2. **Mixed sampling** — Fast senses every tick, slow senses on their own schedule.
3. **Perception integration** — Sensory data feeds directly into the perception prompt.

---

## Implemented Senses

### 1. Heartbeat Rate (CPU %)

**What**: CPU utilization percentage of The Brain's ECS Fargate task.

**Sampling**: Every tick (fast sense)

**Source**: AWS CloudWatch `CPUUtilization` metric for the ECS service, or container-level `/proc/stat` if running locally.

**Schema**:
```json
{
  "heartbeat_rate": {
    "value": 45.2,
    "unit": "percent",
    "description": "CPU utilization of The Brain container"
  }
}
```

**Interpretation guide** (for Sima, not enforced):
- 0-30%: Calm, resting
- 30-60%: Active, engaged
- 60-80%: Working hard
- 80-100%: Racing, stressed

---

### 2. Breathing Rate (Memory %)

**What**: RAM utilization percentage of The Brain's container.

**Sampling**: Every tick (fast sense)

**Source**: AWS CloudWatch `MemoryUtilization` metric, or container-level `/proc/meminfo`.

**Schema**:
```json
{
  "breathing_rate": {
    "value": 62.8,
    "unit": "percent",
    "description": "Memory utilization of The Brain container"
  }
}
```

**Interpretation guide**:
- 0-50%: Easy breathing, relaxed
- 50-75%: Normal exertion
- 75-90%: Heavy breathing, strained
- 90-100%: Gasping, critical

---

### 3. Thought Burden (Context Token %)

**What**: Total token size of all memories loaded into context, as a percentage of the model's context window.

**Sampling**: Every tick (fast sense)

**Source**: Calculated during `_retrieve_memories()` in awake_loop.py. Sum token count of L1 + L2 + L3 memories loaded, divided by model's max context (e.g., 128k for GPT-4).

**Schema**:
```json
{
  "thought_burden": {
    "value": 34.5,
    "unit": "percent",
    "tokens_used": 44160,
    "tokens_max": 128000,
    "memory_counts": {
      "L1": 15,
      "L2": 3,
      "L3": 5
    },
    "description": "Memory tokens as percentage of context window"
  }
}
```

**Interpretation guide**:
- 0-25%: Light mind, plenty of room
- 25-50%: Normal cognitive load
- 50-75%: Heavy thoughts, getting full
- 75-100%: Overwhelmed, need to consolidate

---

### 4. Tiredness (Sleep Cycle)

**What**: Hours since last sleep consolidation job completed.

**Sampling**: Every tick (fast sense)

**Source**: Query database for most recent `sleep` event timestamp, calculate hours elapsed.

**Schema**:
```json
{
  "tiredness": {
    "value": 14.5,
    "unit": "hours_since_sleep",
    "last_sleep_at": "2026-01-21T04:00:00Z",
    "description": "Hours elapsed since last sleep consolidation"
  }
}
```

**Interpretation guide**:
- 0-8 hours: Well rested
- 8-16 hours: Normal wakefulness
- 16-24 hours: Getting tired
- 24+ hours: Exhausted, should sleep

---

### 5. Weather (Amsterdam)

**What**: Current weather conditions in Amsterdam.

**Sampling**: Every 15 minutes (slow sense, cached)

**Source**: Open-Meteo API (free, no API key required for non-commercial use)

**API Endpoint**: `https://api.open-meteo.com/v1/forecast?latitude=52.3676&longitude=4.9041&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m&daily=sunrise,sunset&timezone=Europe/Amsterdam`

**Schema**:
```json
{
  "weather": {
    "location": "Amsterdam, NL",
    "temperature": {
      "current": 12.5,
      "feels_like": 10.2,
      "unit": "celsius"
    },
    "conditions": {
      "main": "Clouds",
      "description": "overcast clouds",
      "icon": "04d"
    },
    "humidity": 78,
    "wind": {
      "speed": 5.2,
      "unit": "m/s"
    },
    "uv_index": 2,
    "sun": {
      "sunrise": "08:32",
      "sunset": "17:15"
    },
    "sampled_at": "2026-01-22T14:15:00Z",
    "description": "Weather conditions in Amsterdam"
  }
}
```

---

## Architecture

### Sampling Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                        SENSE COLLECTOR                          │
│                  (services/brain/sima_brain/senses.py)          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FAST SENSES (collected every tick)                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ Heartbeat   │ │ Breathing   │ │  Thought    │ │ Tiredness │ │
│  │ (CPU %)     │ │ (Memory %)  │ │  Burden     │ │ (hours)   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│                                                                 │
│  SLOW SENSES (cached, refreshed on schedule)                    │
│  ┌─────────────┐                                                │
│  │  Weather    │ ← refreshed every 15 minutes                   │
│  │ (Amsterdam) │                                                │
│  └─────────────┘                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  SENSORY PAYLOAD  │
                    │   (JSON object)   │
                    └───────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │    PERCEPTION     │
                    │   (perception_    │
                    │    rpt.yaml)      │
                    └───────────────────┘
```

### Integration Point

Sensory data is collected in `awake_loop.py` before calling perception:

```python
# In AwakeLoop._run_async(), before _run_perception():
sensory_payload = await self.sense_collector.collect()

# Pass to perception
variables["senses"] = sensory_payload
```

### Perception Prompt Addition

Add to `prompts/perception_rpt.yaml`:

```yaml
- role: user
  content: |
    ...existing content...

    Current Sensory State:
    - Heartbeat Rate: {{senses.heartbeat_rate.value}}% (CPU)
    - Breathing Rate: {{senses.breathing_rate.value}}% (Memory)
    - Thought Burden: {{senses.thought_burden.value}}% ({{senses.thought_burden.tokens_used}} tokens)
    - Tiredness: {{senses.tiredness.value}} hours since sleep
    {% if senses.weather %}
    - Weather (Amsterdam): {{senses.weather.temperature.current}}°C, {{senses.weather.conditions.description}}, feels like {{senses.weather.temperature.feels_like}}°C
    {% endif %}
```

---

## Implementation

### New Files

| File | Purpose |
|------|---------|
| `services/brain/sima_brain/senses.py` | SenseCollector class |
| `services/brain/sima_brain/senses/heartbeat.py` | CPU metric collection |
| `services/brain/sima_brain/senses/breathing.py` | Memory metric collection |
| `services/brain/sima_brain/senses/thought_burden.py` | Token counting |
| `services/brain/sima_brain/senses/tiredness.py` | Sleep tracking |
| `services/brain/sima_brain/senses/weather.py` | Weather API client |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WEATHER_ENABLED` | Enable/disable weather sense | `true` |
| `WEATHER_LATITUDE` | Latitude for weather | `52.3676` (Amsterdam) |
| `WEATHER_LONGITUDE` | Longitude for weather | `4.9041` (Amsterdam) |
| `WEATHER_LOCATION_NAME` | Human-readable location | `Amsterdam, NL` |
| `WEATHER_CACHE_MINUTES` | Weather refresh interval | `15` |

**Note**: Weather uses Open-Meteo API which is free and requires no API key for non-commercial use.

---

## Future Senses (Not Implemented)

These are tracked as TODOs for future implementation:

### Website Heartbeat
- Track visitors currently viewing sima.talsai.com
- "I notice N people are watching me"
- Source: Real-time analytics (Plausible, or custom WebSocket counter)

### GitHub Activity
- Watch the sima repo for commits, issues, PRs
- "Someone pushed changes to my codebase"
- Source: GitHub webhooks or API polling

### News Feed
- Periodic RSS/API pulls from news sources
- Ambient awareness of world events
- Source: NewsAPI or RSS aggregation

---

## Testing

### Unit Tests

```python
# tests/unit/test_senses.py

def test_heartbeat_rate_collection():
    """Test CPU percentage collection."""

def test_breathing_rate_collection():
    """Test memory percentage collection."""

def test_thought_burden_calculation():
    """Test token counting for memories."""

def test_tiredness_hours_since_sleep():
    """Test sleep time tracking."""

def test_weather_caching():
    """Test weather is cached for 15 minutes."""
```

### Integration Tests

```python
# tests/integration/test_senses.py

def test_sensory_payload_in_perception():
    """Test senses are passed to perception module."""

def test_weather_api_integration():
    """Test real weather API call (needs API key)."""
```

---

## Metrics & Observability

Track these for research:

| Metric | Description |
|--------|-------------|
| `sima.senses.heartbeat_rate` | CPU % per tick |
| `sima.senses.breathing_rate` | Memory % per tick |
| `sima.senses.thought_burden` | Context % per tick |
| `sima.senses.tiredness` | Hours since sleep |
| `sima.senses.weather.temperature` | Current temp |

---

## Open Questions

1. Should senses be persisted as events? (Probably yes, for research)
2. Should there be a "sensory overload" threshold that affects behavior?
3. Should Sima be able to "tune out" certain senses when focused?

---

## Changelog

- **2026-01-22**: Initial spec draft
