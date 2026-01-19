"""
Event API routes.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from sima_core.types import Actor, EventType, Stream
from sima_storage.database import get_session
from sima_storage.repository import EventRepository

from ..auth import require_lab_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["events"])


class EventDetail(BaseModel):
    """Event detail response."""
    event_id: str
    trace_id: str
    ts: str
    actor: str
    stream: str
    event_type: str
    content_text: str | None
    content_json: dict | None
    model_provider: str | None
    model_id: str | None
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int | None
    cost_usd: float | None
    parent_event_id: str | None
    tags: list[str]


class EventListResponse(BaseModel):
    """Event list response."""
    events: list[EventDetail]
    total: int


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: UUID,
    _: Annotated[bool, Depends(require_lab_auth)],
):
    """
    Get event detail by ID.

    Lab-only endpoint.
    """
    async with get_session() as session:
        repo = EventRepository(session)
        event = await repo.get(event_id)

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return EventDetail(
            event_id=str(event.event_id),
            trace_id=str(event.trace_id),
            ts=event.ts.isoformat(),
            actor=event.actor.value if hasattr(event.actor, 'value') else str(event.actor),
            stream=event.stream.value if hasattr(event.stream, 'value') else str(event.stream),
            event_type=event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
            content_text=event.content_text,
            content_json=event.content_json,
            model_provider=event.model_provider,
            model_id=event.model_id,
            tokens_in=event.tokens_in,
            tokens_out=event.tokens_out,
            latency_ms=event.latency_ms,
            cost_usd=event.cost_usd,
            parent_event_id=str(event.parent_event_id) if event.parent_event_id else None,
            tags=event.tags or [],
        )


@router.get("", response_model=EventListResponse)
async def list_events(
    _: Annotated[bool, Depends(require_lab_auth)],
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    stream: str | None = Query(None),
):
    """
    List recent events with filtering.

    Lab-only endpoint.
    """
    async with get_session() as session:
        repo = EventRepository(session)

        # Parse stream filter
        filter_stream = None
        if stream:
            try:
                filter_stream = Stream(stream)
            except ValueError:
                pass

        events = await repo.list_recent(
            limit=limit,
            offset=offset,
            stream=filter_stream,
        )

        items = [
            EventDetail(
                event_id=str(e.event_id),
                trace_id=str(e.trace_id),
                ts=e.ts.isoformat(),
                actor=e.actor.value if hasattr(e.actor, 'value') else str(e.actor),
                stream=e.stream.value if hasattr(e.stream, 'value') else str(e.stream),
                event_type=e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type),
                content_text=e.content_text,
                content_json=e.content_json,
                model_provider=e.model_provider,
                model_id=e.model_id,
                tokens_in=e.tokens_in,
                tokens_out=e.tokens_out,
                latency_ms=e.latency_ms,
                cost_usd=e.cost_usd,
                parent_event_id=str(e.parent_event_id) if e.parent_event_id else None,
                tags=e.tags or [],
            )
            for e in events
        ]

        return EventListResponse(
            events=items,
            total=len(items),
        )


@router.get("/search")
async def search_events(
    _: Annotated[bool, Depends(require_lab_auth)],
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Full-text search events.

    Lab-only endpoint.
    """
    async with get_session() as session:
        repo = EventRepository(session)

        try:
            events = await repo.search_content(q, limit=limit)

            items = [
                {
                    "event_id": str(e.event_id),
                    "trace_id": str(e.trace_id),
                    "ts": e.ts.isoformat(),
                    "actor": e.actor.value if hasattr(e.actor, 'value') else str(e.actor),
                    "content_text": e.content_text[:200] if e.content_text else None,
                }
                for e in events
            ]

            return {"results": items, "query": q}
        except Exception as e:
            logger.warning(f"Search failed (BM25 may not be configured): {e}")
            return {"results": [], "query": q, "error": "Search not available"}
