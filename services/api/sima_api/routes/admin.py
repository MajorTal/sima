"""
Admin API routes for system control.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from sima_storage.database import get_session
from sima_storage.repository import SystemStateRepository

from ..auth import require_lab_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


class SystemStatus(BaseModel):
    """System status response."""
    paused: bool
    status: str


class PauseRequest(BaseModel):
    """Pause/resume request."""
    paused: bool


@router.get("/status", response_model=SystemStatus)
async def get_system_status(
    _: Annotated[bool, Depends(require_lab_auth)],
):
    """
    Get system status.

    Lab-only endpoint.
    """
    async with get_session() as session:
        repo = SystemStateRepository(session)
        paused = await repo.is_paused()

        return SystemStatus(
            paused=paused,
            status="paused" if paused else "running",
        )


@router.post("/pause", response_model=SystemStatus)
async def set_system_paused(
    request: PauseRequest,
    _: Annotated[bool, Depends(require_lab_auth)],
):
    """
    Pause or resume the system.

    Lab-only endpoint.
    """
    async with get_session() as session:
        repo = SystemStateRepository(session)
        await repo.set_paused(request.paused)

        action = "paused" if request.paused else "resumed"
        logger.info(f"System {action} by admin")

        return SystemStatus(
            paused=request.paused,
            status="paused" if request.paused else "running",
        )


@router.post("/trigger-tick")
async def trigger_tick(
    _: Annotated[bool, Depends(require_lab_auth)],
    tick_type: str = "autonomous",
):
    """
    Manually trigger a tick event.

    Lab-only endpoint.
    """
    # Would enqueue a tick event to SQS
    logger.info(f"Manual {tick_type} tick triggered by admin")
    return {"status": "triggered", "tick_type": tick_type}
