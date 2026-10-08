"""
Agenda routes — PATCH (edit items), POST approve-send.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.activity_log import ActivityLog
from app.models.agenda import Agenda
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.schemas import AgendaPatchRequest
from app.services.google_workspace import gmail_send

router = APIRouter(tags=["agenda"])


@router.patch("/api/meetings/{meeting_id}/agenda", status_code=204)
async def update_agenda(
    meeting_id: uuid.UUID,
    body: AgendaPatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit agenda items (while in pending_hitl status)."""
    # Verify ownership
    meeting_stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    meeting_result = await db.execute(meeting_stmt)
    if not meeting_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Meeting not found")

    stmt = select(Agenda).where(Agenda.meeting_id == meeting_id)
    result = await db.execute(stmt)
    agenda = result.scalar_one_or_none()
    if not agenda:
        raise HTTPException(status_code=404, detail="Agenda not found")

    agenda.items = [item.model_dump() for item in body.items]
    await db.commit()


@router.post("/api/meetings/{meeting_id}/agenda/approve-send", status_code=204)
async def approve_and_send_agenda(
    meeting_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve and send the agenda via Gmail to all attendees."""
    meeting_stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    meeting_result = await db.execute(meeting_stmt)
    meeting = meeting_result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    stmt = select(Agenda).where(Agenda.meeting_id == meeting_id)
    result = await db.execute(stmt)
    agenda = result.scalar_one_or_none()
    if not agenda:
        raise HTTPException(status_code=404, detail="Agenda not found")

    # Send via Gmail
    attendee_emails = [a["email"] for a in (meeting.attendees or []) if a.get("email")]
    if attendee_emails:
        agenda_items = agenda.items or []
        body_html = f"""
        <h2>Meeting Agenda: {meeting.title}</h2>
        <p>Scheduled: {meeting.start_time.strftime('%B %d, %Y at %I:%M %p')}</p>
        <h3>Agenda Items:</h3>
        <ol>
        {''.join([f"<li>{item.get('text', '')}</li>" for item in agenda_items])}
        </ol>
        <p><em>Sent via MeetingPilot</em></p>
        """
        gmail_send(
            user=user,
            to=attendee_emails,
            subject=f"Meeting Agenda: {meeting.title}",
            body=body_html,
        )

    # Update status
    agenda.status = "sent"
    agenda.sent_at = datetime.now(timezone.utc)

    # Activity log
    activity = ActivityLog(
        id=uuid.uuid4(),
        user_id=user.id,
        meeting_id=meeting.id,
        action=f"Agenda sent for {meeting.title}",
    )
    db.add(activity)
    await db.commit()
