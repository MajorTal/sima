"""
WebSocket endpoint for real-time event streaming.
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from sima_core.types import Stream
from sima_storage.database import get_session
from sima_storage.repository import EventRepository

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {
            "all": [],
            "external": [],
            "conscious": [],
            "subconscious": [],
            "memories": [],
        }

    async def connect(self, websocket: WebSocket, stream: str = "all"):
        """Accept and track a new connection."""
        await websocket.accept()
        if stream not in self.active_connections:
            stream = "all"
        self.active_connections[stream].append(websocket)
        logger.info(f"WebSocket connected to stream: {stream}")

    def disconnect(self, websocket: WebSocket, stream: str = "all"):
        """Remove a connection."""
        if stream in self.active_connections:
            try:
                self.active_connections[stream].remove(websocket)
            except ValueError:
                pass
        logger.info(f"WebSocket disconnected from stream: {stream}")

    async def broadcast(self, message: dict[str, Any], stream: str = "all"):
        """Broadcast message to all connections in a stream."""
        targets = []
        if stream in self.active_connections:
            targets.extend(self.active_connections[stream])
        # Also send to "all" subscribers
        if stream != "all":
            targets.extend(self.active_connections["all"])

        disconnected = []
        for connection in targets:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append((connection, stream))

        # Clean up disconnected
        for conn, s in disconnected:
            self.disconnect(conn, s)


manager = ConnectionManager()


@router.websocket("/ws/events")
async def websocket_events(
    websocket: WebSocket,
    stream: str = Query("all"),
):
    """
    WebSocket endpoint for streaming events.

    Connect to receive real-time events as they are persisted.
    Filter by stream: all, external, conscious, subconscious, memories.
    Polls database every 5 seconds for new events.
    """
    await manager.connect(websocket, stream)

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "stream": stream,
        })

        # Track last seen event timestamp for polling
        from datetime import datetime, timezone
        last_poll_time = datetime.now(timezone.utc)

        while True:
            try:
                # Check for client messages (e.g., ping) with short timeout
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=5.0,  # Poll every 5 seconds
                )

                if data == "ping":
                    await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                # Poll for new events
                try:
                    async with get_session() as session:
                        repo = EventRepository(session)
                        # Get stream filter
                        stream_filter = None
                        if stream != "all":
                            try:
                                stream_filter = Stream(stream)
                            except ValueError:
                                pass

                        # Get recent events
                        events = await repo.list_recent(
                            limit=10,
                            stream=stream_filter,
                        )

                        # Send events newer than last poll
                        for event in reversed(events):  # oldest first
                            if event.ts > last_poll_time:
                                await websocket.send_json({
                                    "type": "event",
                                    "data": {
                                        "event_id": str(event.event_id),
                                        "trace_id": str(event.trace_id),
                                        "ts": event.ts.isoformat(),
                                        "actor": event.actor,
                                        "stream": event.stream,
                                        "event_type": event.event_type,
                                        "content_text": event.content_text,
                                        "content_json": event.content_json,
                                    },
                                })

                        last_poll_time = datetime.now(timezone.utc)

                except Exception as e:
                    logger.warning(f"Failed to poll events: {e}")

                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, stream)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, stream)


async def broadcast_event(event_data: dict[str, Any]):
    """
    Broadcast an event to WebSocket subscribers.

    Called when a new event is persisted.
    """
    stream = event_data.get("stream", "subconscious")
    await manager.broadcast(
        {
            "type": "event",
            "data": event_data,
        },
        stream=stream,
    )


async def broadcast_memory(memory_data: dict[str, Any]):
    """
    Broadcast a memory update to WebSocket subscribers.

    Called when a new memory is created or updated.
    """
    await manager.broadcast(
        {
            "type": "memory",
            "data": memory_data,
        },
        stream="memories",
    )
