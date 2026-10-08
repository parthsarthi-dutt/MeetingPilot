"""
Meetings routes — list, detail, simulate, redo, reschedule, quick-message, workflow-logs.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.mcp.client import GoogleWorkspaceMCPClient
from app.models.activity_log import ActivityLog
from app.models.agenda import Agenda
from app.models.checklist import Checklist as ChecklistModel
from app.models.meeting import Meeting
from app.models.meeting_report import MeetingReport
from app.models.user import User
from app.models.workflow_log import WorkflowLog
from app.schemas.schemas import (
    AgendaItemSchema,
    AgendaSchema,
    AttendeeSchema,
    ChecklistSchema,
    MeetingDetailResponse,
    MeetingSchema,
    MeetingsListResponse,
    QuickMessageRequest,
    RescheduleMeetingRequest,
    RescheduleMeetingResponse,
    SimulateMeetingRequest,
    SimulateMeetingResponse,
    SourcesUsedSchema,
    WorkflowLogEntrySchema,
)
from app.services.google_workspace import calendar_cancel_event, calendar_create_event, gmail_send
from app.worker import enqueue_meeting

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


@router.get("", response_model=MeetingsListResponse)
async def list_meetings(
    status: str | None = None,
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List meetings with optional status filter and pagination."""
    page_size = 20
    query = select(Meeting, func.count().over().label("total_count")).where(Meeting.user_id == user.id)

    if status:
        query = query.where(Meeting.status == status)

    # Paginate
    query = query.order_by(Meeting.start_time.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.all()
    
    meetings = [row[0] for row in rows]
    total = rows[0][1] if rows else 0

    return MeetingsListResponse(
        meetings=[
            MeetingSchema(
                id=m.id,
                title=m.title,
                start_time=m.start_time,
                end_time=m.end_time,
                meet_link=m.meet_link,
                attendees=[AttendeeSchema(**a) for a in (m.attendees or [])],
                status=m.status,
                is_simulated=m.is_simulated,
            )
            for m in meetings
        ],
        total=total,
    )


@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting_detail(
    meeting_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full meeting detail including report, agenda, checklist."""
    stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Load related data
    report_stmt = select(MeetingReport).where(MeetingReport.meeting_id == meeting_id)
    report_result = await db.execute(report_stmt)
    report = report_result.scalar_one_or_none()

    agenda_stmt = select(Agenda).where(Agenda.meeting_id == meeting_id)
    agenda_result = await db.execute(agenda_stmt)
    agenda = agenda_result.scalar_one_or_none()

    checklist_stmt = select(ChecklistModel).where(ChecklistModel.meeting_id == meeting_id)
    checklist_result = await db.execute(checklist_stmt)
    checklist = checklist_result.scalar_one_or_none()

    return MeetingDetailResponse(
        id=meeting.id,
        title=meeting.title,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
        meet_link=meeting.meet_link,
        attendees=[AttendeeSchema(**a) for a in (meeting.attendees or [])],
        status=meeting.status,
        is_simulated=meeting.is_simulated,
        insight_report=report.insight_report if report else None,
        handout=report.handout if report else None,
        sources_used=SourcesUsedSchema(**(report.sources_used or {})) if report else None,
        agenda=AgendaSchema(
            items=[AgendaItemSchema(**i) for i in (agenda.items or [])],
            status=agenda.status,
        ) if agenda else None,
        checklist=ChecklistSchema(
            items=checklist.items or [],
            status=checklist.status,
        ) if checklist else None,
        rescheduled_from_id=meeting.rescheduled_from_id,
        rescheduled_to_id=meeting.rescheduled_to_id,
    )


@router.post("/simulate", response_model=SimulateMeetingResponse)
async def simulate_meeting(
    body: SimulateMeetingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a simulated meeting and queue it for workflow processing."""
    meeting = Meeting(
        id=uuid.uuid4(),
        user_id=user.id,
        title=body.title,
        description=body.description,
        start_time=body.start_time,
        end_time=body.end_time,
        attendees=[a.model_dump() for a in body.attendees],
        status="queued",
        is_simulated=True,
    )
    db.add(meeting)

    # Activity log
    activity = ActivityLog(
        id=uuid.uuid4(),
        user_id=user.id,
        meeting_id=meeting.id,
        action=f"Simulated meeting created: {body.title}",
    )
    db.add(activity)
    await db.commit()

    # Enqueue for workflow processing
    await enqueue_meeting(meeting.id, user.id)

    return SimulateMeetingResponse(meeting_id=meeting.id)


@router.post("/{meeting_id}/redo", status_code=204)
async def redo_workflow(
    meeting_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-queue a meeting's workflow (fresh mode)."""
    stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting.status = "queued"
    meeting.workflow_mode = "fresh"
    await db.commit()

    await enqueue_meeting(meeting.id, user.id)


@router.post("/{meeting_id}/reschedule", response_model=RescheduleMeetingResponse)
async def reschedule_meeting(
    meeting_id: uuid.UUID,
    body: RescheduleMeetingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Postpone/prepone a meeting — creates new event, copies data, cancels original."""
    stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    result = await db.execute(stmt)
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Create new calendar event
    try:
        new_event = calendar_create_event(
            user=user,
            summary=original.title,
            start_time=body.new_start_time,
            end_time=body.new_end_time,
            attendees=original.attendees or [],
            description=original.description or "",
        )
    except Exception:
        new_event = {}

    # Create new meeting row
    new_meeting = Meeting(
        id=uuid.uuid4(),
        user_id=user.id,
        google_event_id=new_event.get("id"),
        title=original.title,
        description=original.description,
        start_time=body.new_start_time,
        end_time=body.new_end_time,
        meet_link=new_event.get("hangoutLink"),
        attendees=original.attendees,
        status="processed",  # Copies existing data, no re-run
        is_simulated=original.is_simulated,
        rescheduled_from_id=original.id,
    )
    db.add(new_meeting)

    # Copy report, agenda, checklist
    report_stmt = select(MeetingReport).where(MeetingReport.meeting_id == original.id)
    report_result = await db.execute(report_stmt)
    original_report = report_result.scalar_one_or_none()
    if original_report:
        new_report = MeetingReport(
            id=uuid.uuid4(),
            meeting_id=new_meeting.id,
            insight_report=original_report.insight_report,
            handout=original_report.handout,
            sources_used=original_report.sources_used,
        )
        db.add(new_report)

    agenda_stmt = select(Agenda).where(Agenda.meeting_id == original.id)
    agenda_result = await db.execute(agenda_stmt)
    original_agenda = agenda_result.scalar_one_or_none()
    if original_agenda:
        new_agenda = Agenda(
            id=uuid.uuid4(),
            meeting_id=new_meeting.id,
            items=original_agenda.items,
            status=original_agenda.status,
        )
        db.add(new_agenda)

    checklist_stmt = select(ChecklistModel).where(ChecklistModel.meeting_id == original.id)
    checklist_result = await db.execute(checklist_stmt)
    original_checklist = checklist_result.scalar_one_or_none()
    if original_checklist:
        new_checklist = ChecklistModel(
            id=uuid.uuid4(),
            meeting_id=new_meeting.id,
            items=original_checklist.items,
            status=original_checklist.status,
        )
        db.add(new_checklist)

    # Update original
    original.status = "rescheduled"
    original.rescheduled_to_id = new_meeting.id

    # Cancel original calendar event
    if original.google_event_id:
        try:
            calendar_cancel_event(user, original.google_event_id)
        except Exception:
            pass

    # Activity log
    activity = ActivityLog(
        id=uuid.uuid4(),
        user_id=user.id,
        meeting_id=original.id,
        action=f"Meeting rescheduled to {body.new_start_time.strftime('%B %d, %Y')}",
    )
    db.add(activity)

    await db.commit()

    return RescheduleMeetingResponse(new_meeting_id=new_meeting.id)


@router.post("/{meeting_id}/quick-message", status_code=204)
async def send_quick_message(
    meeting_id: uuid.UUID,
    body: QuickMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a quick message to meeting attendees."""
    stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Build message
    if body.template == "looking_forward":
        text = f"Hi! Looking forward to our meeting: {meeting.title}. See you soon!"
    else:
        text = body.text or "Hello!"

    # Send to all attendees
    attendee_emails = [a["email"] for a in (meeting.attendees or []) if a.get("email")]
    if attendee_emails:
        gmail_send(
            user=user,
            to=attendee_emails,
            subject=f"Re: {meeting.title}",
            body=f"<p>{text}</p><p><em>Sent via MeetingPilot</em></p>",
        )

    # Activity log
    activity = ActivityLog(
        id=uuid.uuid4(),
        user_id=user.id,
        meeting_id=meeting.id,
        action=f"Quick message sent for {meeting.title}",
    )
    db.add(activity)
    await db.commit()


@router.get("/{meeting_id}/workflow-logs", response_model=list[WorkflowLogEntrySchema])
async def get_workflow_logs(
    meeting_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get workflow logs for a meeting."""
    # Verify meeting belongs to user
    meeting_stmt = select(Meeting).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
    meeting_result = await db.execute(meeting_stmt)
    if not meeting_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Meeting not found")

    stmt = (
        select(WorkflowLog)
        .where(WorkflowLog.meeting_id == meeting_id)
        .order_by(WorkflowLog.started_at)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return [
        WorkflowLogEntrySchema(
            node_name=log.node_name,
            status=log.status,
            message=log.message,
            metadata=log.metadata_,
            started_at=log.started_at,
            completed_at=log.completed_at,
        )
        for log in logs
    ]

@router.post("/{meeting_id}/agenda/approve-send", status_code=204)
async def approve_and_send_agenda(
    meeting_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually approve and send the agenda via email to external attendees."""
    from sqlalchemy.orm import selectinload
    
    stmt = select(Meeting).options(selectinload(Meeting.agenda)).where(
        Meeting.id == meeting_id, Meeting.user_id == user.id
    )
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.agenda:
        raise HTTPException(status_code=400, detail="Agenda not generated yet")

    # Get attendees emails
    all_attendee_emails = [
        a["email"] for a in meeting.attendees if a.get("email") and a.get("is_external")
    ]
    if not all_attendee_emails:
        raise HTTPException(status_code=400, detail="No external attendees found to send to")

    try:
        body = f"""
        <h2>Meeting Agenda: {meeting.title}</h2>
        <p>Scheduled: {meeting.start_time.strftime('%B %d, %Y at %I:%M %p')}</p>
        <h3>Agenda Items:</h3>
        <ol>
        {''.join([f"<li>{item['text']}</li>" for item in meeting.agenda.items])}
        </ol>
        <p><em>Sent via MeetingPilot</em></p>
        """

        async with GoogleWorkspaceMCPClient(
            access_token=user.access_token or "",
            refresh_token=user.refresh_token or "",
        ) as gws_client:
            await gws_client.gmail_send(
                to=", ".join(all_attendee_emails),
                subject=f"Meeting Agenda: {meeting.title}",
                body=body,
            )

        meeting.agenda.status = "sent"
        meeting.agenda.sent_at = datetime.now(timezone.utc)
        
        # Log activity
        activity = ActivityLog(
            id=uuid.uuid4(),
            user_id=user.id,
            meeting_id=meeting.id,
            action=f"Manually approved and sent agenda to {len(all_attendee_emails)} attendees",
        )
        db.add(activity)
        await db.commit()
    except Exception as e:
        import logging
        logging.error(f"[Meetings API] Failed to send agenda: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
