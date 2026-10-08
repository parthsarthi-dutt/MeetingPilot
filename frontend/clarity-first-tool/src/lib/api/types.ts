// MeetingPilot API contract types.
// Source of truth: /API-CONTRACT.md — do not diverge here without updating the contract.

export type MeetingStatus =
  | "not_processed"
  | "queued"
  | "processing"
  | "processed"
  | "done"
  | "rescheduled"
  | "failed";

export type AgendaStatus = "draft" | "pending_hitl" | "approved" | "sent";
export type ChecklistStatus = "not_started" | "in_progress" | "ready_to_send" | "sent";
export type KbStatus = "not_started" | "in_progress" | "complete";
export type WorkflowNodeStatus = "started" | "success" | "skipped" | "failed" | "retried";

export interface Attendee {
  name: string;
  email: string;
  company?: string;
  is_external?: boolean;
}

export interface Meeting {
  id: string;
  title: string;
  start_time: string; // ISO
  end_time: string;
  meet_link?: string;
  attendees: Attendee[];
  status: MeetingStatus;
  is_simulated: boolean;
}

export interface AgendaItem {
  id: string;
  text: string;
  order: number;
}

export interface Agenda {
  items: AgendaItem[];
  status: AgendaStatus;
}

export interface ChecklistComment {
  author: string;
  text: string;
  ts: string;
}

export interface ChecklistItem {
  agenda_item_id: string;
  ticked_by: string[];
  comments: ChecklistComment[];
}

export interface Checklist {
  items: ChecklistItem[];
  status: ChecklistStatus;
}

export interface SourcesUsed {
  osint: boolean;
  direct_search: boolean;
  rag: boolean;
}

export interface InsightReport {
  summary: string;
  key_findings: string[];
  attendee_briefs: {
    name: string;
    role: string;
    company: string;
    notes: string[];
  }[];
}

export interface Handout {
  headline: string;
  talking_points: string[];
  questions_to_ask: string[];
}

export interface MeetingDetail extends Meeting {
  insight_report: InsightReport;
  handout: Handout;
  sources_used: SourcesUsed;
  agenda: Agenda;
  checklist: Checklist;
  rescheduled_from_id?: string;
  rescheduled_to_id?: string;
}

export interface WorkflowLogEntry {
  node_name: string;
  status: WorkflowNodeStatus;
  message: string;
  metadata: Record<string, unknown>;
  started_at: string;
  completed_at?: string;
}

export interface OnboardingStatus {
  permissions_complete: boolean;
  granted_scopes: string[];
  company_profile_complete: boolean;
  kb_status: KbStatus;
  kb_progress_pct: number;
}

export interface CompanyProfile {
  company_name: string;
  product_description: string;
  value_proposition: string;
  user_role_title: string;
}

export interface Settings {
  agent_enabled: boolean;
  agent_sub_toggles: Record<string, boolean>;
  always_rerun_osint: boolean;
  auto_send_agenda: boolean;
  auto_send_checklist: boolean;
  is_admin: boolean;
  company_profile?: CompanyProfile;
}

export interface Credits {
  used_count: number;
  total_allowed: number;
}

export interface AdminOverview {
  total_users: number;
  meetings_by_status: Record<MeetingStatus, number>;
  total_credits_used: number;
  total_reports: number;
  total_agendas_sent: number;
  total_checklists_sent: number;
  avg_workflow_time_ms: number;
  failed_workflow_count: number;
}

export interface AdminUserRow {
  email: string;
  signup_date: string;
  permissions_complete: boolean;
  credits_used: number;
  credits_total: number;
  meetings_processed: number;
  reports_generated: number;
  agendas_sent: number;
  checklists_sent: number;
  kb_status: KbStatus;
  last_active: string;
}
