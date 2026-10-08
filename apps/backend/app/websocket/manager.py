"""
WebSocket connection manager.
Handles authenticated dashboard connections and meeting-scoped checklist channels.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Dict, List, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages two kinds of WebSocket connections:
    1. Per-user connections (dashboard: meeting_status_changed, workflow_log_appended, kb_progress)
    2. Per-meeting connections (checklist sync: checklist_tick, checklist_comment, checklist_updated)
    """

    def __init__(self):
        # user_id -> list of active websocket connections
        self._user_connections: Dict[uuid.UUID, List[WebSocket]] = {}
        # meeting_id -> set of websocket connections (for checklist broadcast)
        self._meeting_connections: Dict[uuid.UUID, Set[WebSocket]] = {}

    async def connect_user(self, user_id: uuid.UUID, websocket: WebSocket):
        """Register a user's dashboard WS connection."""
        await websocket.accept()
        if user_id not in self._user_connections:
            self._user_connections[user_id] = []
        self._user_connections[user_id].append(websocket)
        logger.info(f"[WS] User {user_id} connected (total: {len(self._user_connections[user_id])})")

    def disconnect_user(self, user_id: uuid.UUID, websocket: WebSocket):
        """Remove a user's WS connection."""
        if user_id in self._user_connections:
            self._user_connections[user_id] = [
                ws for ws in self._user_connections[user_id] if ws != websocket
            ]
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]

    async def join_meeting(self, meeting_id: uuid.UUID, websocket: WebSocket):
        """Subscribe a WS connection to a meeting's checklist channel."""
        if meeting_id not in self._meeting_connections:
            self._meeting_connections[meeting_id] = set()
        self._meeting_connections[meeting_id].add(websocket)
        logger.info(f"[WS] Joined meeting {meeting_id} checklist channel")

    def leave_meeting(self, meeting_id: uuid.UUID, websocket: WebSocket):
        """Unsubscribe from a meeting's checklist channel."""
        if meeting_id in self._meeting_connections:
            self._meeting_connections[meeting_id].discard(websocket)
            if not self._meeting_connections[meeting_id]:
                del self._meeting_connections[meeting_id]

    async def send_to_user(self, user_id: uuid.UUID, data: dict):
        """Send an event to all of a user's active connections."""
        connections = self._user_connections.get(user_id, [])
        dead: list = []
        for ws in connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_user(user_id, ws)

    async def broadcast_to_meeting(self, meeting_id: uuid.UUID, data: dict):
        """Broadcast an event to all connections watching a meeting (checklist sync)."""
        connections = self._meeting_connections.get(meeting_id, set())
        dead: list = []
        for ws in connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.leave_meeting(meeting_id, ws)

    async def send_meeting_status_changed(
        self, user_id: uuid.UUID, meeting_id: uuid.UUID, status: str
    ):
        """Helper: send meeting_status_changed event."""
        await self.send_to_user(user_id, {
            "event": "meeting_status_changed",
            "meeting_id": str(meeting_id),
            "status": status,
        })

    async def send_workflow_log_appended(
        self, user_id: uuid.UUID, meeting_id: uuid.UUID, log_entry: dict
    ):
        """Helper: send workflow_log_appended event."""
        await self.send_to_user(user_id, {
            "event": "workflow_log_appended",
            "meeting_id": str(meeting_id),
            "log_entry": log_entry,
        })

    async def send_kb_progress(
        self, user_id: uuid.UUID, progress_pct: int, status: str
    ):
        """Helper: send kb_progress event."""
        await self.send_to_user(user_id, {
            "event": "kb_progress",
            "progress_pct": progress_pct,
            "status": status,
        })

    async def send_checklist_updated(
        self, meeting_id: uuid.UUID, checklist: dict
    ):
        """Helper: broadcast checklist_updated to all meeting participants."""
        await self.broadcast_to_meeting(meeting_id, {
            "event": "checklist_updated",
            "checklist": checklist,
        })


# Singleton — imported by API routes and workflow nodes
ws_manager = ConnectionManager()
