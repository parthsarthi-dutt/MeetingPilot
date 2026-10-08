"""
Checklist routes — GET and POST send.
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
from app.models.checklist import Checklist as ChecklistModel
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.schemas import ChecklistSchema
from app.services.google_workspace import gmail_send
from pydantic import BaseModel

router = APIRouter(tags=["checklist"])


@router.get("/api/meetings/{meeting_id}/checklist", response_model=ChecklistSchema)
async def get_checklist(
    meeting_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the checklist for a meeting."""
    meeting_stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    meeting_result = await db.execute(meeting_stmt)
    if not meeting_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Meeting not found")

    stmt = select(ChecklistModel).where(ChecklistModel.meeting_id == meeting_id)
    result = await db.execute(stmt)
    checklist = result.scalar_one_or_none()

    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    # Build agenda lookup for backfilling text on older items that lack it
    agenda_stmt = select(Agenda).where(Agenda.meeting_id == meeting_id)
    agenda_result = await db.execute(agenda_stmt)
    agenda = agenda_result.scalar_one_or_none()
    agenda_text_map = {}
    if agenda and agenda.items:
        for a_item in agenda.items:
            agenda_text_map[str(a_item.get("id", ""))] = a_item.get("text", "")

    # Enrich items: backfill text from agenda if not already stored on the item
    enriched_items = []
    for item in (checklist.items or []):
        if not item.get("text"):
            item = dict(item)
            item["text"] = agenda_text_map.get(str(item.get("agenda_item_id", "")), "")
        enriched_items.append(item)

    return ChecklistSchema(
        items=enriched_items,
        status=checklist.status,
    )

class ChecklistPatchRequest(BaseModel):
    items: list[dict]

@router.patch("/api/meetings/{meeting_id}/checklist", status_code=204)
async def update_checklist(
    meeting_id: uuid.UUID,
    body: ChecklistPatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update checklist items (checked state and comments) from the extension."""
    meeting_stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    meeting_result = await db.execute(meeting_stmt)
    if not meeting_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Meeting not found")

    stmt = select(ChecklistModel).where(ChecklistModel.meeting_id == meeting_id)
    result = await db.execute(stmt)
    checklist = result.scalar_one_or_none()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    # Update items JSONB
    checklist.items = body.items
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(checklist, "items")
    await db.commit()


@router.post("/api/meetings/{meeting_id}/checklist/send", status_code=204)
async def send_checklist(
    meeting_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually send the checklist to all meeting participants."""
    meeting_stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    meeting_result = await db.execute(meeting_stmt)
    meeting = meeting_result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    stmt = select(ChecklistModel).where(ChecklistModel.meeting_id == meeting_id)
    result = await db.execute(stmt)
    checklist = result.scalar_one_or_none()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    # Build checklist email
    items = checklist.items or []
    # Get agenda items for text
    agenda_stmt = select(Agenda).where(Agenda.meeting_id == meeting_id)
    agenda_result = await db.execute(agenda_stmt)
    agenda = agenda_result.scalar_one_or_none()
    agenda_items = {str(i.get("id", "")): i.get("text", "") for i in (agenda.items if agenda else [])}

    checklist_html = "<h2>Meeting Checklist</h2><ul>"
    for item in items:
        aid = item.get("agenda_item_id", "")
        text = agenda_items.get(aid, aid)
        ticked = "✅" if item.get("ticked_by") else "⬜"
        comments_html = ""
        for c in item.get("comments", []):
            comments_html += f"<br>&nbsp;&nbsp;💬 {c.get('author', '')}: {c.get('text', '')}"
        checklist_html += f"<li>{ticked} {text}{comments_html}</li>"
    checklist_html += "</ul><p><em>Sent via MeetingPilot</em></p>"

    attendee_emails = [a["email"] for a in (meeting.attendees or []) if a.get("email")]
    if attendee_emails:
        gmail_send(
            user=user,
            to=attendee_emails,
            subject=f"Meeting Checklist: {meeting.title}",
            body=checklist_html,
        )

    checklist.status = "sent"
    checklist.sent_at = datetime.now(timezone.utc)

    activity = ActivityLog(
        id=uuid.uuid4(),
        user_id=user.id,
        meeting_id=meeting.id,
        action=f"Checklist sent for {meeting.title}",
    )
    db.add(activity)
    await db.commit()
