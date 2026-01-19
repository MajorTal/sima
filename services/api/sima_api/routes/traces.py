"""
Trace API routes.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from sima_core.types import InputType
from sima_storage.database import get_session
from sima_storage.repository import TraceRepository, EventRepository

from ..auth import require_lab_auth, optional_lab_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/traces", tags=["traces"])


class TraceListItem(BaseModel):
    """Trace list item."""
    trace_id: str
    input_type: str
    started_at: str
    completed_at: str | None
    user_message: str | None
    response_message: str | None
    total_tokens: int
    total_cost_usd: float


class TraceDetail(BaseModel):
    """Trace detail."""
    trace_id: str
    input_type: str
    started_at: str
    completed_at: str | None
    telegram_chat_id: int | None
    telegram_message_id: int | None
    user_message: str | None
    response_message: str | None
    total_tokens: int
    total_cost_usd: float
    events: list[dict]


class TraceListResponse(BaseModel):
    """Trace list response."""
    traces: list[TraceListItem]
    total: int
    limit: int
    offset: int


@router.get("", response_model=TraceListResponse)
async def list_traces(
    _: Annotated[bool, Depends(optional_lab_auth)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    input_type: str | None = Query(None),
):
    """
    List traces with pagination.

    Public endpoint - returns limited info without auth.
    """
    async with get_session() as session:
        repo = TraceRepository(session)

        # Parse input type if provided
        filter_input_type = None
        if input_type:
            try:
                filter_input_type = InputType(input_type)
            except ValueError:
                pass

        traces = await repo.list_recent(
            limit=limit,
            offset=offset,
            input_type=filter_input_type,
        )
        total = await repo.count(input_type=filter_input_type)

        items = [
            TraceListItem(
                trace_id=str(t.trace_id),
                input_type=t.input_type.value if hasattr(t.input_type, 'value') else str(t.input_type),
                started_at=t.started_at.isoformat(),
                completed_at=t.completed_at.isoformat() if t.completed_at else None,
                user_message=t.user_message[:100] if t.user_message else None,
                response_message=t.response_message[:100] if t.response_message else None,
                total_tokens=t.total_tokens or 0,
                total_cost_usd=t.total_cost_usd or 0.0,
            )
            for t in traces
        ]

        return TraceListResponse(
            traces=items,
            total=total,
            limit=limit,
            offset=offset,
        )


@router.get("/{trace_id}", response_model=TraceDetail)
async def get_trace(
    trace_id: UUID,
    _: Annotated[bool, Depends(require_lab_auth)],
    include_events: bool = Query(True),
):
    """
    Get trace detail with events.

    Lab-only endpoint - requires authentication.
    """
    async with get_session() as session:
        trace_repo = TraceRepository(session)
        event_repo = EventRepository(session)

        trace = await trace_repo.get(trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")

        events = []
        if include_events:
            event_models = await event_repo.list_by_trace(trace_id)
            events = [
                {
                    "event_id": str(e.event_id),
                    "ts": e.ts.isoformat(),
                    "actor": e.actor.value if hasattr(e.actor, 'value') else str(e.actor),
                    "stream": e.stream.value if hasattr(e.stream, 'value') else str(e.stream),
                    "event_type": e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type),
                    "content_text": e.content_text,
                    "content_json": e.content_json,
                    "model_provider": e.model_provider,
                    "model_id": e.model_id,
                    "tokens_in": e.tokens_in,
                    "tokens_out": e.tokens_out,
                    "latency_ms": e.latency_ms,
                    "cost_usd": e.cost_usd,
                }
                for e in event_models
            ]

        return TraceDetail(
            trace_id=str(trace.trace_id),
            input_type=trace.input_type.value if hasattr(trace.input_type, 'value') else str(trace.input_type),
            started_at=trace.started_at.isoformat(),
            completed_at=trace.completed_at.isoformat() if trace.completed_at else None,
            telegram_chat_id=trace.telegram_chat_id,
            telegram_message_id=trace.telegram_message_id,
            user_message=trace.user_message,
            response_message=trace.response_message,
            total_tokens=trace.total_tokens or 0,
            total_cost_usd=trace.total_cost_usd or 0.0,
            events=events,
        )


@router.get("/{trace_id}/public")
async def get_trace_public(trace_id: UUID):
    """
    Get public trace info (limited data, no auth required).
    """
    async with get_session() as session:
        trace_repo = TraceRepository(session)
        trace = await trace_repo.get(trace_id)

        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")

        return {
            "trace_id": str(trace.trace_id),
            "input_type": trace.input_type.value if hasattr(trace.input_type, 'value') else str(trace.input_type),
            "started_at": trace.started_at.isoformat(),
            "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
            "user_message": trace.user_message[:200] if trace.user_message else None,
            "response_message": trace.response_message,
        }
