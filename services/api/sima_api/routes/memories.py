"""
Memory API routes for the public website.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from sima_storage.database import get_session
from sima_storage.repository import MemoryRepository

from ..auth import optional_lab_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memories", tags=["memories"])


class MemoryItem(BaseModel):
    """Memory list item."""
    memory_id: str
    memory_type: str
    content: str
    created_at: str
    updated_at: str
    relevance_score: float
    access_count: int
    metadata_json: dict | None


class MemoryListResponse(BaseModel):
    """Memory list response."""
    memories: list[MemoryItem]
    total: int
    limit: int
    offset: int


class CoreMemoriesResponse(BaseModel):
    """Core memories (L3) response."""
    core_memories: list[MemoryItem]
    recent_memories: list[MemoryItem]


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    _: Annotated[bool, Depends(optional_lab_auth)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    memory_type: str | None = Query(None, description="Filter by memory type: L1, L2, or L3"),
):
    """
    List memories with pagination.

    Public endpoint - no auth required.
    Memory types:
    - L1: Short-term / episodic memories
    - L2: Consolidated memories
    - L3: Core / identity memories
    """
    async with get_session() as session:
        repo = MemoryRepository(session)

        if memory_type:
            memories = await repo.list_by_type(memory_type, limit=limit)
            # Apply offset manually since list_by_type doesn't support it
            memories = memories[offset:offset + limit] if offset > 0 else memories[:limit]
        else:
            # Get all memory types, prioritizing L3
            all_memories = []
            for mt in ["L3", "L2", "L1"]:
                type_memories = await repo.list_by_type(mt, limit=limit)
                all_memories.extend(type_memories)
            # Sort by relevance_score descending
            all_memories.sort(key=lambda m: m.relevance_score, reverse=True)
            memories = all_memories[offset:offset + limit]

        items = [
            MemoryItem(
                memory_id=str(m.memory_id),
                memory_type=m.memory_type,
                content=m.content,
                created_at=m.created_at.isoformat(),
                updated_at=m.updated_at.isoformat(),
                relevance_score=m.relevance_score,
                access_count=m.access_count,
                metadata_json=m.metadata_json,
            )
            for m in memories
        ]

        return MemoryListResponse(
            memories=items,
            total=len(items),
            limit=limit,
            offset=offset,
        )


@router.get("/core", response_model=CoreMemoriesResponse)
async def get_core_memories(
    _: Annotated[bool, Depends(optional_lab_auth)],
    core_limit: int = Query(10, ge=1, le=50),
    recent_limit: int = Query(20, ge=1, le=100),
):
    """
    Get core (L3) memories and recent consolidated memories.

    Returns L3 core memories at the top, followed by recent L1/L2.
    This is the primary endpoint for the Memories panel.
    """
    async with get_session() as session:
        repo = MemoryRepository(session)

        # Get L3 core memories (sorted by relevance)
        core_memories = await repo.list_by_type("L3", limit=core_limit)

        # Get recent L1/L2 memories
        l1_memories = await repo.list_by_type("L1", limit=recent_limit)
        l2_memories = await repo.list_by_type("L2", limit=recent_limit)

        # Combine and sort L1/L2 by created_at descending
        recent = list(l1_memories) + list(l2_memories)
        recent.sort(key=lambda m: m.created_at, reverse=True)
        recent = recent[:recent_limit]

        return CoreMemoriesResponse(
            core_memories=[
                MemoryItem(
                    memory_id=str(m.memory_id),
                    memory_type=m.memory_type,
                    content=m.content,
                    created_at=m.created_at.isoformat(),
                    updated_at=m.updated_at.isoformat(),
                    relevance_score=m.relevance_score,
                    access_count=m.access_count,
                    metadata_json=m.metadata_json,
                )
                for m in core_memories
            ],
            recent_memories=[
                MemoryItem(
                    memory_id=str(m.memory_id),
                    memory_type=m.memory_type,
                    content=m.content,
                    created_at=m.created_at.isoformat(),
                    updated_at=m.updated_at.isoformat(),
                    relevance_score=m.relevance_score,
                    access_count=m.access_count,
                    metadata_json=m.metadata_json,
                )
                for m in recent
            ],
        )


@router.get("/{memory_id}", response_model=MemoryItem)
async def get_memory(
    memory_id: UUID,
    _: Annotated[bool, Depends(optional_lab_auth)],
):
    """
    Get a single memory by ID.

    Public endpoint.
    """
    async with get_session() as session:
        repo = MemoryRepository(session)
        memory = await repo.get(memory_id)

        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        # Record access
        await repo.record_access(memory_id)
        await session.commit()

        return MemoryItem(
            memory_id=str(memory.memory_id),
            memory_type=memory.memory_type,
            content=memory.content,
            created_at=memory.created_at.isoformat(),
            updated_at=memory.updated_at.isoformat(),
            relevance_score=memory.relevance_score,
            access_count=memory.access_count + 1,  # Include current access
            metadata_json=memory.metadata_json,
        )


@router.get("/search")
async def search_memories(
    _: Annotated[bool, Depends(optional_lab_auth)],
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Search memories using BM25 full-text search.

    Public endpoint.
    """
    async with get_session() as session:
        repo = MemoryRepository(session)

        try:
            memories = await repo.search(q, limit=limit)

            items = [
                MemoryItem(
                    memory_id=str(m.memory_id),
                    memory_type=m.memory_type,
                    content=m.content,
                    created_at=m.created_at.isoformat(),
                    updated_at=m.updated_at.isoformat(),
                    relevance_score=m.relevance_score,
                    access_count=m.access_count,
                    metadata_json=m.metadata_json,
                )
                for m in memories
            ]

            return {"results": items, "query": q}
        except Exception as e:
            logger.warning(f"Memory search failed (BM25 may not be configured): {e}")
            return {"results": [], "query": q, "error": "Search not available"}
