"""
Pydantic schemas — all request/response shapes matching API-CONTRACT.md exactly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Onboarding ───────────────────────────────────────────────

class OnboardingStatusResponse(BaseModel):
    permissions_complete: bool
    granted_scopes: List[str]
    company_profile_complete: bool
    kb_status: Literal["not_started", "in_progress", "complete"]
    kb_progress_pct: int


# ─── Company Profile ──────────────────────────────────────────

class CompanyProfileRequest(BaseModel):
    company_name: str
    product_description: str
    value_proposition: str
    user_role_title: str


class CompanyProfileResponse(BaseModel):
    company_name: str
    product_description: str
    value_proposition: str
    user_role_title: str


# ─── Meetings ─────────────────────────────────────────────────

class AttendeeSchema(BaseModel):
    name: str
    email: str
    is_external: Optional[bool] = None
    company: Optional[str] = None


class MeetingSchema(BaseModel):
    id: UUID
    title: str
    start_time: datetime
    end_time: datetime
    meet_link: Optional[str] = None
    attendees: List[AttendeeSchema]
    status: Literal[
        "not_processed", "queued", "processing",
        "processed", "done", "rescheduled", "failed"
    ]
    is_simulated: bool


class MeetingsListResponse(BaseModel):
    meetings: List[MeetingSchema]
    total: int


class AgendaItemSchema(BaseModel):
    id: str
    text: str
    order: int


class AgendaSchema(BaseModel):
    items: List[AgendaItemSchema]
    status: Literal["draft", "pending_hitl", "approved", "sent"]


class ChecklistCommentSchema(BaseModel):
    author: str
    text: str
    ts: datetime


class ChecklistItemSchema(BaseModel):
    agenda_item_id: str
    text: Optional[str] = None
    ticked_by: List[str]
    comments: List[ChecklistCommentSchema]


class ChecklistSchema(BaseModel):
    items: List[ChecklistItemSchema]
    status: Literal["not_started", "in_progress", "ready_to_send", "sent"]


class SourcesUsedSchema(BaseModel):
    osint: bool = False
    direct_search: bool = False
    rag: bool = False


class MeetingDetailResponse(BaseModel):
    """MeetingDetail — extends Meeting per API contract."""
    id: UUID
    title: str
    start_time: datetime
    end_time: datetime
    meet_link: Optional[str] = None
    attendees: List[AttendeeSchema]
    status: str
    is_simulated: bool
    insight_report: Optional[Any] = None
    handout: Optional[Any] = None
    sources_used: Optional[SourcesUsedSchema] = None
    agenda: Optional[AgendaSchema] = None
    checklist: Optional[ChecklistSchema] = None
    rescheduled_from_id: Optional[UUID] = None
    rescheduled_to_id: Optional[UUID] = None


class SimulateMeetingRequest(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[AttendeeSchema]


class SimulateMeetingResponse(BaseModel):
    meeting_id: UUID


class RescheduleMeetingRequest(BaseModel):
    new_start_time: datetime
    new_end_time: datetime


class RescheduleMeetingResponse(BaseModel):
    new_meeting_id: UUID


class QuickMessageRequest(BaseModel):
    template: Literal["looking_forward", "custom"]
    text: Optional[str] = None


# ─── Agenda ───────────────────────────────────────────────────

class AgendaPatchRequest(BaseModel):
    items: List[AgendaItemSchema]


# ─── Contacts ─────────────────────────────────────────────────

class DoNotResearchRequest(BaseModel):
    value: bool


# ─── Settings ─────────────────────────────────────────────────

class CompanyProfilePatchRequest(BaseModel):
    company_name: Optional[str] = None
    product_description: Optional[str] = None
    value_proposition: Optional[str] = None
    user_role_title: Optional[str] = None


class SettingsResponse(BaseModel):
    agent_enabled: bool
    agent_sub_toggles: Dict[str, Any]
    always_rerun_osint: bool
    auto_send_agenda: bool
    auto_send_checklist: bool
    is_admin: bool
    company_profile: Optional[CompanyProfileResponse] = None


class SettingsPatchRequest(BaseModel):
    agent_enabled: Optional[bool] = None
    agent_sub_toggles: Optional[Dict[str, Any]] = None
    always_rerun_osint: Optional[bool] = None
    auto_send_agenda: Optional[bool] = None
    auto_send_checklist: Optional[bool] = None
    company_profile: Optional[CompanyProfilePatchRequest] = None


class ConnectionsResponse(BaseModel):
    granted_scopes: List[str]
    permissions_complete: bool


class ReconnectGoogleResponse(BaseModel):
    redirect_url: str


# ─── Credits ──────────────────────────────────────────────────

class CreditsResponse(BaseModel):
    used_count: int
    total_allowed: int


# ─── Extension ────────────────────────────────────────────────

class ExtensionMeetingResponse(BaseModel):
    meeting_id: UUID
    agenda_items: List[AgendaItemSchema]
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ExtensionUpcomingMeeting(BaseModel):
    id: UUID
    title: str
    start_time: datetime
    end_time: datetime
    meet_link: Optional[str] = None


# ─── Workflow Logs ────────────────────────────────────────────

class WorkflowLogEntrySchema(BaseModel):
    node_name: str
    status: Literal["started", "success", "skipped", "failed", "retried"]
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


# ─── Admin ────────────────────────────────────────────────────

class AdminOverviewResponse(BaseModel):
    total_users: int
    meetings_by_status: Dict[str, int]
    total_credits_used: int
    total_reports: int
    total_agendas_sent: int
    total_checklists_sent: int
    avg_workflow_time_ms: float
    failed_workflow_count: int


class AdminUserRow(BaseModel):
    email: str
    signup_date: datetime
    permissions_complete: bool
    credits_used: int
    credits_total: int
    meetings_processed: int
    reports_generated: int
    agendas_sent: int
    checklists_sent: int
    kb_status: Optional[str] = None
    last_active: Optional[datetime] = None


# ─── WebSocket Events ────────────────────────────────────────

class WSMeetingStatusChanged(BaseModel):
    event: str = "meeting_status_changed"
    meeting_id: UUID
    status: str


class WSWorkflowLogAppended(BaseModel):
    event: str = "workflow_log_appended"
    meeting_id: UUID
    log_entry: WorkflowLogEntrySchema


class WSKBProgress(BaseModel):
    event: str = "kb_progress"
    progress_pct: int
    status: str


class WSChecklistTick(BaseModel):
    meeting_id: UUID
    agenda_item_id: str
    ticked: bool


class WSChecklistComment(BaseModel):
    meeting_id: UUID
    agenda_item_id: str
    text: str


class WSChecklistUpdated(BaseModel):
    event: str = "checklist_updated"
    checklist: ChecklistSchema
