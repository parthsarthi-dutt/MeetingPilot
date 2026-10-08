"""
Extension-facing route — meeting lookup by Meet link.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.agenda import Agenda
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.schemas import AgendaItemSchema, ExtensionMeetingResponse, ExtensionUpcomingMeeting

router = APIRouter(prefix="/api/extension", tags=["extension"])


@router.get("/meeting-by-link")
async def get_meeting_by_link(
    meet_link: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Look up a meeting by its Google Meet link (used by the extension)."""
    stmt = select(Meeting).where(
        Meeting.user_id == user.id,
        Meeting.meet_link == meet_link,
    )
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()

    if not meeting:
        # ── Fallback: the meet link may have been regenerated after we synced ──
        # Fetch the user's recent Calendar events and see if any event now has
        # this hangoutLink. If so, update the DB and carry on as normal.
        import asyncio
        from app.services.google_workspace import calendar_get_upcoming_events

        try:
            events = await asyncio.to_thread(calendar_get_upcoming_events, user, 50)
            matched_event = next(
                (e for e in events if e.get("hangoutLink") == meet_link),
                None
            )
            if matched_event:
                google_event_id = matched_event.get("id")
                # Find the DB meeting by its google_event_id (original sync handle)
                stmt2 = select(Meeting).where(
                    Meeting.user_id == user.id,
                    Meeting.google_event_id == google_event_id,
                )
                result2 = await db.execute(stmt2)
                meeting = result2.scalar_one_or_none()

                if meeting:
                    # Update the stored link so future lookups are instant
                    meeting.meet_link = meet_link
                    await db.commit()
        except Exception:
            pass  # If Calendar API fails, fall through to None return

    if not meeting:
        return None

    # Load agenda
    agenda_stmt = select(Agenda).where(Agenda.meeting_id == meeting.id)
    agenda_result = await db.execute(agenda_stmt)
    agenda = agenda_result.scalar_one_or_none()

    agenda_items = []
    if agenda:
        agenda_items = [
            AgendaItemSchema(id=i.get("id", ""), text=i.get("text", ""), order=i.get("order", 0))
            for i in (agenda.items or [])
        ]

    return ExtensionMeetingResponse(
        meeting_id=meeting.id,
        agenda_items=agenda_items,
        title=meeting.title,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
    )


@router.get("/upcoming-meetings", response_model=list[ExtensionUpcomingMeeting])
async def get_upcoming_meetings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all upcoming meetings for today (and beyond) for the user."""
    from datetime import datetime, timezone, timedelta
    
    # Get start of today in UTC (rough approximation, could use user timezone if available)
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    stmt = select(Meeting).where(
        Meeting.user_id == user.id,
        Meeting.end_time >= start_of_today
    ).order_by(Meeting.start_time.asc())
    
    result = await db.execute(stmt)
    meetings = result.scalars().all()
    
    return [
        ExtensionUpcomingMeeting(
            id=m.id,
            title=m.title,
            start_time=m.start_time,
            end_time=m.end_time,
            meet_link=m.meet_link,
        )
        for m in meetings
    ]

from fastapi import BackgroundTasks
import asyncio
from datetime import datetime, timezone
from app.models.checklist import Checklist as ChecklistModel
from app.services.google_workspace import gmail_send

async def auto_send_checklist_task(meeting_id: uuid.UUID, user_id: int):
    # This task runs in the background. It will wait until end_time if needed, then send.
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        # Re-fetch user and meeting
        user_stmt = select(User).where(User.id == user_id)
        user = (await db.execute(user_stmt)).scalar_one_or_none()
        meeting_stmt = select(Meeting).where(Meeting.id == meeting_id)
        meeting = (await db.execute(meeting_stmt)).scalar_one_or_none()
        
        if not user or not meeting or not user.auto_send_checklist:
            return
            
        now = datetime.now(timezone.utc)
        if meeting.end_time and meeting.end_time > now:
            delay = (meeting.end_time - now).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)
                
        # Send checklist
        checklist_stmt = select(ChecklistModel).where(ChecklistModel.meeting_id == meeting_id)
        checklist = (await db.execute(checklist_stmt)).scalar_one_or_none()
        if not checklist or not checklist.items:
            return
            
        if checklist.status == "sent":
            return
            
        html_body = f"<h2>Checklist for: {meeting.title}</h2><ul>"
        for item in checklist.items:
            checked = "[x]" if item.get("ticked_by") else "[ ]"
            html_body += f"<li>{checked} {item.get('text', '')}"
            comments = item.get("comments", [])
            if comments:
                html_body += "<ul>"
                for c in comments:
                    html_body += f"<li><i>{c.get('author')}: {c.get('text')}</i></li>"
                html_body += "</ul>"
            html_body += "</li>"
        html_body += "</ul>"

        emails = [a["email"] for a in meeting.attendees] if meeting.attendees else []
        if emails:
            await gmail_send(user, emails, f"Post-Meeting Checklist: {meeting.title}", html_body)
            checklist.status = "sent"
            checklist.sent_at = datetime.now(timezone.utc)
            await db.commit()

@router.post("/meet-closed", status_code=204)
async def meet_closed(
    background_tasks: BackgroundTasks,
    meet_link: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Webhook triggered when the extension unloads (tab closes)."""
    stmt = select(Meeting).where(
        Meeting.user_id == user.id,
        Meeting.meet_link == meet_link,
    )
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()

    if meeting and user.auto_send_checklist:
        background_tasks.add_task(auto_send_checklist_task, meeting.id, user.id)
