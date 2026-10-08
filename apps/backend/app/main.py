"""
MeetingPilot Backend — FastAPI Application Entry Point
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

import sentry_sdk
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, engine, Base, async_session_factory
from app.websocket.manager import ws_manager
from app.auth.dependencies import get_current_user_ws
from app.models.checklist import Checklist as ChecklistModel
from app.models.meeting import Meeting

# ─── Route imports ────────────────────────────────────────────
from app.api.auth import router as auth_router
from app.api.onboarding import router as onboarding_router
from app.api.meetings import router as meetings_router
from app.api.agenda import router as agenda_router
from app.api.checklist import router as checklist_router
from app.api.contacts import router as contacts_router
from app.api.settings import router as settings_router
from app.api.credits import router as credits_router
from app.api.extension import router as extension_router
from app.api.admin import router as admin_router

# ─── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Sentry ───────────────────────────────────────────────────
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
    )

# ─── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="MeetingPilot API",
    description="Autonomous meeting intelligence agent backend",
    version="1.0.0",
)

# ─── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routers ────────────────────────────────────────
app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(meetings_router)
app.include_router(agenda_router)
app.include_router(checklist_router)
app.include_router(contacts_router)
app.include_router(settings_router)
app.include_router(credits_router)
app.include_router(extension_router)
app.include_router(admin_router)


# ─── Background Tasks ─────────────────────────────────────────
background_tasks = set()

# ─── Startup / Shutdown ──────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    """Create tables (dev convenience — use Alembic migrations in production)."""
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await conn.run_sync(Base.metadata.create_all)

    logger.info("MeetingPilot backend started")

    # Start the worker in the background (same process for dev simplicity)
    from app.worker import worker_loop
    task = asyncio.create_task(worker_loop())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    # Start the calendar poller in the background
    from app.services.calendar_poller import calendar_poller
    poller_task = asyncio.create_task(calendar_poller())
    background_tasks.add(poller_task)
    poller_task.add_done_callback(background_tasks.discard)


@app.on_event("shutdown")
async def on_shutdown():
    await engine.dispose()
    logger.info("MeetingPilot backend shut down")


# ─── Health Check ─────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "meetingpilot-backend"}


# ─── WebSocket Endpoint ──────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Single WS connection per authenticated session.
    Handles dashboard events and checklist sync.
    """
    async with async_session_factory() as db:
        user = await get_current_user_ws(websocket, db)

    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await ws_manager.connect_user(user.id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if event == "join_meeting":
                meeting_id = uuid.UUID(data["meeting_id"])
                await ws_manager.join_meeting(meeting_id, websocket)

            elif event == "leave_meeting":
                meeting_id = uuid.UUID(data["meeting_id"])
                ws_manager.leave_meeting(meeting_id, websocket)

            elif event == "checklist_tick":
                meeting_id = uuid.UUID(data["meeting_id"])
                agenda_item_id = data["agenda_item_id"]
                ticked = data["ticked"]

                # Update checklist in DB
                async with async_session_factory() as db:
                    stmt = select(ChecklistModel).where(
                        ChecklistModel.meeting_id == meeting_id
                    )
                    result = await db.execute(stmt)
                    checklist = result.scalar_one_or_none()

                    if checklist:
                        items = checklist.items or []
                        for item in items:
                            if item.get("agenda_item_id") == agenda_item_id:
                                ticked_by = item.get("ticked_by", [])
                                user_email = user.email
                                if ticked and user_email not in ticked_by:
                                    ticked_by.append(user_email)
                                elif not ticked and user_email in ticked_by:
                                    ticked_by.remove(user_email)
                                item["ticked_by"] = ticked_by
                                break

                        # Update status
                        any_ticked = any(
                            len(i.get("ticked_by", [])) > 0 for i in items
                        )
                        if checklist.status != "sent":
                            checklist.status = "in_progress" if any_ticked else "not_started"

                        checklist.items = items
                        await db.commit()

                        # Broadcast to all clients on this meeting
                        await ws_manager.send_checklist_updated(meeting_id, {
                            "items": items,
                            "status": checklist.status,
                        })

            elif event == "checklist_comment":
                meeting_id = uuid.UUID(data["meeting_id"])
                agenda_item_id = data["agenda_item_id"]
                text = data["text"]

                async with async_session_factory() as db:
                    stmt = select(ChecklistModel).where(
                        ChecklistModel.meeting_id == meeting_id
                    )
                    result = await db.execute(stmt)
                    checklist = result.scalar_one_or_none()

                    if checklist:
                        items = checklist.items or []
                        from datetime import datetime, timezone
                        for item in items:
                            if item.get("agenda_item_id") == agenda_item_id:
                                comments = item.get("comments", [])
                                comments.append({
                                    "author": user.email,
                                    "text": text,
                                    "ts": datetime.now(timezone.utc).isoformat(),
                                })
                                item["comments"] = comments
                                break

                        if checklist.status not in ("sent",):
                            checklist.status = "in_progress"

                        checklist.items = items
                        await db.commit()

                        await ws_manager.send_checklist_updated(meeting_id, {
                            "items": items,
                            "status": checklist.status,
                        })

    except WebSocketDisconnect:
        ws_manager.disconnect_user(user.id, websocket)
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
        ws_manager.disconnect_user(user.id, websocket)


# ─── Calendar Webhook ─────────────────────────────────────────
@app.post("/api/webhooks/calendar")
async def calendar_webhook(
    request_body: dict = {},
):
    """
    Google Calendar push notification webhook.
    Called when a calendar event is created/updated.
    """
    # In production, verify the webhook token and process the notification
    # For now, this is a placeholder that will be fully wired when
    # calendar watch is registered for each user
    logger.info(f"[Webhook] Calendar notification received")
    return {"status": "ok"}
