"""
Admin routes — analytics overview and per-user breakdown.
Requires hardcoded admin email check (server-side).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.database import get_db
from app.models.agenda import Agenda
from app.models.checklist import Checklist as ChecklistModel
from app.models.credit_ledger import CreditLedger
from app.models.kb_ingestion_status import KBIngestionStatus
from app.models.meeting import Meeting
from app.models.meeting_report import MeetingReport
from app.models.user import User
from app.models.workflow_log import WorkflowLog
from app.schemas.schemas import AdminOverviewResponse, AdminUserRow

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/analytics/overview", response_model=AdminOverviewResponse)
async def get_admin_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Platform-wide analytics — single query aggregation."""
    require_admin(user)
    from sqlalchemy import text

    query = text("""
    SELECT
        (SELECT COUNT(*) FROM users) as total_users,
        (SELECT COUNT(*) FROM meetings WHERE status = 'not_processed') as not_processed,
        (SELECT COUNT(*) FROM meetings WHERE status = 'queued') as queued,
        (SELECT COUNT(*) FROM meetings WHERE status = 'processing') as processing,
        (SELECT COUNT(*) FROM meetings WHERE status = 'processed') as processed,
        (SELECT COUNT(*) FROM meetings WHERE status = 'done') as done,
        (SELECT COUNT(*) FROM meetings WHERE status = 'rescheduled') as rescheduled,
        (SELECT COUNT(*) FROM meetings WHERE status = 'failed') as failed,
        (SELECT COALESCE(SUM(used_count), 0) FROM credit_ledger) as total_credits_used,
        (SELECT COUNT(*) FROM meeting_reports) as total_reports,
        (SELECT COUNT(*) FROM agendas WHERE status = 'sent') as total_agendas_sent,
        (SELECT COUNT(*) FROM checklists WHERE status = 'sent') as total_checklists_sent,
        (
            SELECT COALESCE(AVG(EXTRACT(EPOCH FROM completed_at) - EXTRACT(EPOCH FROM started_at)) * 1000, 0)
            FROM workflow_logs 
            WHERE status = 'success' AND completed_at IS NOT NULL
        ) as avg_workflow_time_ms,
        (SELECT COUNT(*) FROM meetings WHERE status = 'failed') as failed_workflow_count
    """)
    result = await db.execute(query)
    row = result.fetchone()

    return AdminOverviewResponse(
        total_users=int(row.total_users),
        meetings_by_status={
            "not_processed": int(row.not_processed),
            "queued": int(row.queued),
            "processing": int(row.processing),
            "processed": int(row.processed),
            "done": int(row.done),
            "rescheduled": int(row.rescheduled),
            "failed": int(row.failed),
        },
        total_credits_used=int(row.total_credits_used),
        total_reports=int(row.total_reports),
        total_agendas_sent=int(row.total_agendas_sent),
        total_checklists_sent=int(row.total_checklists_sent),
        avg_workflow_time_ms=float(row.avg_workflow_time_ms),
        failed_workflow_count=int(row.failed_workflow_count),
    )


@router.get("/analytics/users", response_model=list[AdminUserRow])
async def get_admin_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-user breakdown table — single query aggregation."""
    require_admin(user)
    from sqlalchemy import text

    query = text("""
    SELECT 
        u.email,
        u.created_at,
        u.permissions_complete,
        COALESCE(c.used_count, 0) as credits_used,
        COALESCE(c.total_allowed, 2) as credits_total,
        (SELECT COUNT(*) FROM meetings m WHERE m.user_id = u.id AND m.status IN ('processed', 'done')) as meetings_processed,
        (SELECT COUNT(*) FROM meeting_reports mr JOIN meetings m ON mr.meeting_id = m.id WHERE m.user_id = u.id) as reports_generated,
        (SELECT COUNT(*) FROM agendas a JOIN meetings m ON a.meeting_id = m.id WHERE m.user_id = u.id AND a.status = 'sent') as agendas_sent,
        (SELECT COUNT(*) FROM checklists ch JOIN meetings m ON ch.meeting_id = m.id WHERE m.user_id = u.id AND ch.status = 'sent') as checklists_sent,
        COALESCE(kb.status, 'not_started') as kb_status,
        (SELECT MAX(completed_at) FROM workflow_logs w WHERE w.user_id = u.id) as last_active
    FROM users u
    LEFT JOIN credit_ledger c ON c.user_id = u.id
    LEFT JOIN kb_ingestion_status kb ON kb.user_id = u.id
    ORDER BY u.created_at DESC
    """)
    
    result = await db.execute(query)
    rows = result.fetchall()

    return [
        AdminUserRow(
            email=row.email,
            signup_date=row.created_at,
            permissions_complete=row.permissions_complete,
            credits_used=int(row.credits_used),
            credits_total=int(row.credits_total),
            meetings_processed=int(row.meetings_processed),
            reports_generated=int(row.reports_generated),
            agendas_sent=int(row.agendas_sent),
            checklists_sent=int(row.checklists_sent),
            kb_status=row.kb_status,
            last_active=row.last_active,
        )
        for row in rows
    ]
