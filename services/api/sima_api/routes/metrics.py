"""
Metrics API routes for theory indicators.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from sima_core.types import Actor, EventType
from sima_storage.database import get_session
from sima_storage.repository import EventRepository, TraceRepository

from ..auth import require_lab_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/metrics", tags=["metrics"])


class OverviewMetrics(BaseModel):
    """Overview metrics."""
    total_traces: int
    total_events: int
    total_tokens: int
    total_cost_usd: float


class RPTMetrics(BaseModel):
    """Recurrent Processing Theory metrics."""
    avg_recurrence_steps: float
    avg_stability_score: float
    revision_frequency: float


class GWTMetrics(BaseModel):
    """Global Workspace Theory metrics."""
    parallel_module_count: int
    avg_candidates_per_trace: float
    avg_selected_items: float
    broadcast_rate: float


class HOTMetrics(BaseModel):
    """Higher-Order Thought metrics."""
    avg_confidence: float
    belief_revision_rate: float
    metacog_reports_per_trace: float


class ASTMetrics(BaseModel):
    """Attention Schema Theory metrics."""
    prediction_accuracy: float
    focus_shift_rate: float


class TheoryIndicators(BaseModel):
    """All theory indicators."""
    overview: OverviewMetrics
    rpt: RPTMetrics
    gwt: GWTMetrics
    hot: HOTMetrics
    ast: ASTMetrics


@router.get("/overview", response_model=OverviewMetrics)
async def get_overview_metrics(
    _: Annotated[bool, Depends(require_lab_auth)],
):
    """
    Get overview metrics.

    Lab-only endpoint.
    """
    async with get_session() as session:
        trace_repo = TraceRepository(session)
        total_traces = await trace_repo.count()

        # Calculate totals from recent traces
        traces = await trace_repo.list_recent(limit=1000)
        total_tokens = sum(t.total_tokens or 0 for t in traces)
        total_cost = sum(t.total_cost_usd or 0.0 for t in traces)

        # Estimate events
        total_events = total_traces * 10  # Rough estimate

        return OverviewMetrics(
            total_traces=total_traces,
            total_events=total_events,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
        )


@router.get("/indicators", response_model=TheoryIndicators)
async def get_theory_indicators(
    _: Annotated[bool, Depends(require_lab_auth)],
    window_hours: int = Query(24, ge=1, le=168),
):
    """
    Get theory indicators for the specified time window.

    Lab-only endpoint.
    """
    # These would be computed from actual event data
    # For now, return placeholder values
    overview = OverviewMetrics(
        total_traces=0,
        total_events=0,
        total_tokens=0,
        total_cost_usd=0.0,
    )

    rpt = RPTMetrics(
        avg_recurrence_steps=3.0,
        avg_stability_score=0.85,
        revision_frequency=0.15,
    )

    gwt = GWTMetrics(
        parallel_module_count=3,
        avg_candidates_per_trace=12.0,
        avg_selected_items=5.0,
        broadcast_rate=0.95,
    )

    hot = HOTMetrics(
        avg_confidence=0.75,
        belief_revision_rate=0.12,
        metacog_reports_per_trace=1.0,
    )

    ast = ASTMetrics(
        prediction_accuracy=0.68,
        focus_shift_rate=0.22,
    )

    async with get_session() as session:
        trace_repo = TraceRepository(session)
        total_traces = await trace_repo.count()

        traces = await trace_repo.list_recent(limit=100)
        total_tokens = sum(t.total_tokens or 0 for t in traces)
        total_cost = sum(t.total_cost_usd or 0.0 for t in traces)

        overview = OverviewMetrics(
            total_traces=total_traces,
            total_events=total_traces * 10,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
        )

    return TheoryIndicators(
        overview=overview,
        rpt=rpt,
        gwt=gwt,
        hot=hot,
        ast=ast,
    )


@router.get("/timeseries")
async def get_metrics_timeseries(
    _: Annotated[bool, Depends(require_lab_auth)],
    metric: str = Query(...),
    window_hours: int = Query(24, ge=1, le=168),
    resolution_minutes: int = Query(60, ge=5, le=1440),
):
    """
    Get timeseries data for a specific metric.

    Lab-only endpoint.
    """
    # Placeholder - would compute actual timeseries from events
    return {
        "metric": metric,
        "window_hours": window_hours,
        "resolution_minutes": resolution_minutes,
        "data": [],
    }
