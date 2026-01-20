"""
API routes.
"""

from .traces import router as traces_router
from .events import router as events_router
from .metrics import router as metrics_router
from .admin import router as admin_router
from .memories import router as memories_router

__all__ = [
    "traces_router",
    "events_router",
    "metrics_router",
    "admin_router",
    "memories_router",
]
