"""
LangGraph Workflow — 11-node meeting processing graph.
Implements the full pipeline from PRD Section 7.

Graph Nodes:
1. load_meeting_context
2. attendee_classification
3. osint_cache_check (per external attendee)
4. direct_search (per external attendee)
5. rag_retrieval (per external attendee)
6. company_context_injection
7. insight_report_generation (LLM)
8. agenda_draft_generation (LLM)
9. validation_pass
10. persist_and_notify
11. agenda_hitl_gate
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.client import llm_generate, llm_generate_json
from app.mcp.client import OSINTMCPClient, GoogleWorkspaceMCPClient
from app.mcp.osint_server.utils import compute_person_key
from app.models.activity_log import ActivityLog
from app.models.agenda import Agenda
from app.models.checklist import Checklist as ChecklistModel
from app.models.company_profile import CompanyProfile
from app.models.kb_chunk import KBChunk
from app.models.meeting import Meeting
from app.models.meeting_report import MeetingReport
from app.models.workflow_log import WorkflowLog
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict, total=False):
    """State that flows through the LangGraph-style workflow."""
    meeting_id: str
    user_id: str
    meeting: dict
    attendees: list
    external_attendees: list
    internal_attendees: list
    has_external: bool
    person_data: dict  # person_key -> osint/search/rag data
    direct_search_data: dict
    rag_data: dict
    company_profile: dict
    insight_report: dict
    handout: dict
    sources_used: dict
    agenda_items: list
    validation_passed: bool
    error: str | None


async def _log_workflow_step(
    db: AsyncSession,
    meeting_id: uuid.UUID,
    user_id: uuid.UUID,
    node_name: str,
    status: str,
    message: str,
    metadata: dict | None = None,
    started_at: datetime | None = None,
):
    """Write a workflow_logs row and fire a WebSocket event."""
    now = datetime.now(timezone.utc)
    log_entry = WorkflowLog(
        id=uuid.uuid4(),
        meeting_id=meeting_id,
        user_id=user_id,
        node_name=node_name,
        status=status,
        message=message,
        metadata_=metadata or {},
        started_at=started_at or now,
        completed_at=now if status != "started" else None,
    )
    db.add(log_entry)
    await db.flush()

    # Fire WebSocket event
    await ws_manager.send_workflow_log_appended(user_id, meeting_id, {
        "node_name": node_name,
        "status": status,
        "message": message,
        "metadata": metadata or {},
        "started_at": (started_at or now).isoformat(),
        "completed_at": now.isoformat() if status != "started" else None,
    })


async def run_meeting_workflow(
    meeting_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
):
    """Execute the full 11-node LangGraph workflow for a meeting."""

    mid = meeting_id
    uid = user_id

    # Update meeting status to processing
    stmt = select(Meeting).where(Meeting.id == mid)
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()
    if not meeting:
        logger.error(f"[Workflow] Meeting {mid} not found")
        return

    meeting.status = "processing"
    await db.commit()
    await ws_manager.send_meeting_status_changed(uid, mid, "processing")

    try:
        state: WorkflowState = {
            "meeting_id": str(mid),
            "user_id": str(uid),
            "person_data": {},
            "direct_search_data": {},
            "rag_data": {},
        }

        # ─── Node 1: Load Meeting Context ─────────────────────
        t0 = time.time()
        await _log_workflow_step(db, mid, uid, "load_meeting_context", "started",
                                  "Loading meeting context...")

        state["meeting"] = {
            "title": meeting.title,
            "description": meeting.description or "",
            "start_time": meeting.start_time.isoformat(),
            "end_time": meeting.end_time.isoformat(),
        }
        state["attendees"] = meeting.attendees or []

        await _log_workflow_step(db, mid, uid, "load_meeting_context", "success",
                                  f"Loaded meeting: {meeting.title}",
                                  {"duration_ms": int((time.time() - t0) * 1000)},
                                  datetime.fromtimestamp(t0, tz=timezone.utc))

        # ─── Node 2: Attendee Classification ──────────────────
        t0 = time.time()
        await _log_workflow_step(db, mid, uid, "attendee_classification", "started",
                                  "Classifying attendees...")

        # Get user email domain
        user_stmt = select(Meeting).where(Meeting.id == mid)
        user_result = await db.execute(user_stmt)
        # meeting is already fetched above, we can just use meeting.user_id to get user
        from app.models.user import User as UserModel
        user_obj_stmt = select(UserModel).where(UserModel.id == uid)
        user_obj_result = await db.execute(user_obj_stmt)
        user_obj = user_obj_result.scalar_one()
        user_domain = user_obj.email.split("@")[1].lower() if "@" in user_obj.email else ""
        
        generic_domains = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"}

        external = []
        internal = []
        updated_attendees = []
        for att in state["attendees"]:
            # Create a new dict to avoid modifying the sqlalchemy state in-place directly without flag_modified
            new_att = dict(att)
            email = new_att.get("email", "")
            att_domain = email.split("@")[1].lower() if "@" in email else ""
            
            if email.lower() == user_obj.email.lower():
                is_ext = False
            elif att_domain in generic_domains or user_domain in generic_domains:
                is_ext = True
            else:
                is_ext = att_domain != user_domain if att_domain and user_domain else True
                
            new_att["is_external"] = is_ext
            updated_attendees.append(new_att)
            
            if is_ext:
                external.append(new_att)
            else:
                internal.append(new_att)

        state["attendees"] = updated_attendees
        state["external_attendees"] = external
        state["internal_attendees"] = internal
        state["has_external"] = len(external) > 0
        
        # Save classification back to DB so manual send endpoint can read it
        meeting.attendees = updated_attendees
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(meeting, "attendees")
        await db.commit()

        await _log_workflow_step(db, mid, uid, "attendee_classification", "success",
                                  f"Found {len(external)} external, {len(internal)} internal attendees",
                                  {"external_count": len(external), "internal_count": len(internal),
                                   "duration_ms": int((time.time() - t0) * 1000)},
                                  datetime.fromtimestamp(t0, tz=timezone.utc))

        # ─── Nodes 3-5: Per-attendee research (only if external) ──
        if state["has_external"]:
            # Connect to MCP servers — spawns subprocesses via stdio
            async with OSINTMCPClient() as osint_client:
                async with GoogleWorkspaceMCPClient(
                    access_token=user_obj.access_token or "",
                    refresh_token=user_obj.refresh_token or "",
                ) as gws_client:

                    for att in external:
                        person_name = att.get("name", "Unknown")
                        person_email = att.get("email")
                        person_company = att.get("company", "")

                        # Node 3: OSINT via MCP tool call
                        t0 = time.time()
                        await _log_workflow_step(db, mid, uid, "osint_research", "started",
                                                  f"Researching {person_name} via OSINT MCP...")

                        force_rerun = (
                            user_obj.always_rerun_osint or
                            meeting.workflow_mode == "fresh"
                        )

                        # Call research_person tool on the OSINT MCP server
                        osint_result = await osint_client.research_person(
                            name=person_name,
                            company=person_company,
                            email=person_email,
                            user_id=str(uid),
                            force_rerun=force_rerun,
                        )

                        person_key = osint_result.get("person_key", compute_person_key(person_email, person_name, person_company))
                        state["person_data"][person_key] = osint_result

                        status_msg = osint_result.get("status", "unknown")
                        credit_info = " — 1 credit used" if osint_result.get("credit_charged") else ""
                        if status_msg == "cached":
                            msg = f"Reused cached OSINT data for {person_name}"
                        elif status_msg == "credit_exhausted":
                            msg = f"Skipped OSINT for {person_name}: credit limit reached"
                        elif status_msg == "skipped":
                            msg = f"Skipped OSINT for {person_name}: do not research"
                        elif status_msg == "success":
                            msg = f"Researched {person_name} via OSINT MCP{credit_info}"
                        else:
                            msg = f"OSINT {status_msg} for {person_name}"

                        await _log_workflow_step(db, mid, uid, "osint_research",
                                                  "success" if status_msg in ("success", "cached") else
                                                  "skipped" if status_msg in ("skipped", "credit_exhausted") else "failed",
                                                  msg,
                                                  {"person_key": person_key, "credit_charged": osint_result.get("credit_charged", False),
                                                   "duration_ms": osint_result.get("duration_ms", 0),
                                                   "transport": "mcp_stdio"},
                                                  datetime.fromtimestamp(t0, tz=timezone.utc))

                        # Node 4: Direct Search via Google Workspace MCP tools
                        t0 = time.time()
                        await _log_workflow_step(db, mid, uid, "direct_search", "started",
                                                  f"Searching workspace for {person_name} via Google Workspace MCP...")

                        search_query = f"{person_name} {person_company}"
                        direct_results = []
                        try:
                            # Call gmail_search tool on the Google Workspace MCP server
                            gmail_result = await gws_client.gmail_search(search_query, max_results=10)
                            for m in gmail_result.get("messages", []):
                                direct_results.append(
                                    f"Email: {m.get('subject', '')} - {m.get('snippet', '')}"
                                )
                        except Exception as e:
                            logger.warning(f"[Workflow] Gmail MCP search failed: {e}")

                        try:
                            # Call drive_search tool on the Google Workspace MCP server
                            drive_result = await gws_client.drive_search(search_query, max_results=10)
                            for f in drive_result.get("files", []):
                                direct_results.append(
                                    f"File: {f.get('name', '')} ({f.get('mimeType', '')})"
                                )
                        except Exception as e:
                            logger.warning(f"[Workflow] Drive MCP search failed: {e}")

                        # Truncate to word cap
                        combined = "\n".join(direct_results)
                        words = combined.split()
                        if len(words) > settings.direct_search_word_cap:
                            combined = " ".join(words[:settings.direct_search_word_cap])

                        state["direct_search_data"][person_key] = combined

                        await _log_workflow_step(db, mid, uid, "direct_search", "success",
                                                  f"Found {len(direct_results)} workspace items for {person_name}",
                                                  {"items_found": len(direct_results),
                                                   "duration_ms": int((time.time() - t0) * 1000),
                                                   "transport": "mcp_stdio"},
                                                  datetime.fromtimestamp(t0, tz=timezone.utc))

                # Node 5: RAG Retrieval
                t0 = time.time()
                await _log_workflow_step(db, mid, uid, "rag_retrieval", "started",
                                          f"Querying knowledge base for {person_name}...")

                try:
                    from sentence_transformers import SentenceTransformer
                    embedder = SentenceTransformer("all-MiniLM-L6-v2")
                    query_embedding = embedder.encode(search_query).tolist()

                    from pgvector.sqlalchemy import Vector
                    from sqlalchemy import text

                    rag_query = text("""
                        SELECT content, 1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                        FROM kb_chunks
                        WHERE user_id = :user_id
                        ORDER BY embedding <=> CAST(:embedding AS vector)
                        LIMIT 10
                    """)
                    async with db.begin_nested():
                        rag_result = await db.execute(
                            rag_query,
                            {"embedding": str(query_embedding), "user_id": str(uid)}
                        )
                        rag_rows = rag_result.fetchall()
                        rag_text = "\n".join([row[0] for row in rag_rows])

                    # Truncate to word cap
                    rag_words = rag_text.split()
                    if len(rag_words) > settings.rag_retrieval_word_cap:
                        rag_text = " ".join(rag_words[:settings.rag_retrieval_word_cap])

                    state["rag_data"][person_key] = rag_text
                except Exception as e:
                    logger.warning(f"[Workflow] RAG retrieval failed: {e}")
                    state["rag_data"][person_key] = ""


                await _log_workflow_step(db, mid, uid, "rag_retrieval", "success",
                                          f"Retrieved knowledge base context for {person_name}",
                                          {"chunks_found": len(rag_rows) if 'rag_rows' in dir() else 0,
                                           "duration_ms": int((time.time() - t0) * 1000)},
                                          datetime.fromtimestamp(t0, tz=timezone.utc))

        # ─── Node 6: Company Context Injection ────────────────
        t0 = time.time()
        await _log_workflow_step(db, mid, uid, "company_context_injection", "started",
                                  "Loading company context...")

        cp_stmt = select(CompanyProfile).where(CompanyProfile.user_id == uid)
        cp_result = await db.execute(cp_stmt)
        company_profile = cp_result.scalar_one_or_none()

        state["company_profile"] = {
            "company_name": company_profile.company_name if company_profile else "N/A",
            "product_description": company_profile.product_description if company_profile else "",
            "value_proposition": company_profile.value_proposition if company_profile else "",
            "user_role_title": company_profile.user_role_title if company_profile else "",
        }

        await _log_workflow_step(db, mid, uid, "company_context_injection", "success",
                                  f"Loaded company context: {state['company_profile']['company_name']}",
                                  {"duration_ms": int((time.time() - t0) * 1000)},
                                  datetime.fromtimestamp(t0, tz=timezone.utc))

        # ─── Node 7: Insight Report Generation (LLM) ──────────
        t0 = time.time()
        await _log_workflow_step(db, mid, uid, "report_generation", "started",
                                  "Generating insight report...")

        if state["has_external"]:
            # Build per-attendee context
            attendee_sections = []
            for att in state["external_attendees"]:
                pk = compute_person_key(att.get("email"), att.get("name", ""), att.get("company", ""))
                osint = state["person_data"].get(pk, {}).get("osint_data", {})
                direct = state["direct_search_data"].get(pk, "")
                rag = state["rag_data"].get(pk, "")

                attendee_sections.append(f"""
### {att.get('name', 'Unknown')} ({att.get('company', 'N/A')})
**OSINT Data:** {str(osint)[:2000] if osint else 'No OSINT data available'}
**Your Workspace History:** {direct[:1000] if direct else 'No prior interactions found'}
**Knowledge Base:** {rag[:500] if rag else 'No relevant KB entries'}
""")

            schema_example = """{
  "insight_report": {
    "summary": "String summarizing the meeting context",
    "key_findings": ["Array of string key findings"],
    "attendee_briefs": [
      {
        "name": "Attendee name",
        "role": "Attendee role/title",
        "company": "Company name",
        "notes": ["Array of string notes/background"]
      }
    ]
  },
  "handout": {
    "headline": "String headline for the handout",
    "talking_points": ["Array of string talking points"],
    "questions_to_ask": ["Array of string questions to ask"]
  },
  "sources_used": {
    "osint": true,
    "direct_search": true,
    "rag": true
  }
}"""

            report_prompt = f"""Generate a comprehensive meeting insight report.

**Meeting:** {state['meeting']['title']}
**Description:** {state['meeting']['description']}
**Your Company:** {state['company_profile']['company_name']}
**Your Product:** {state['company_profile']['product_description']}
**Your Value Proposition:** {state['company_profile']['value_proposition']}
**Your Role:** {state['company_profile']['user_role_title']}

**External Attendees Research:**
{''.join(attendee_sections)}

Generate a JSON response matching this EXACT schema:
{schema_example}
"""
            report_data = llm_generate_json(
                prompt=report_prompt,
                system_prompt="You are a meeting intelligence assistant. Generate structured meeting prep reports in JSON format.",
            )
        else:
            report_data = {
                "insight_report": {"note": "Internal meeting — no external attendee research needed"},
                "handout": {"note": "Internal meeting"},
                "sources_used": {"osint": False, "direct_search": False, "rag": False},
            }

        state["insight_report"] = report_data.get("insight_report", {})
        state["handout"] = report_data.get("handout", {})
        state["sources_used"] = report_data.get("sources_used", {"osint": False, "direct_search": False, "rag": False})

        await _log_workflow_step(db, mid, uid, "report_generation", "success",
                                  "Insight report generated",
                                  {"duration_ms": int((time.time() - t0) * 1000)},
                                  datetime.fromtimestamp(t0, tz=timezone.utc))

        # ─── Node 8: Agenda Draft Generation (LLM) ────────────
        t0 = time.time()
        await _log_workflow_step(db, mid, uid, "agenda_draft", "started",
                                  "Drafting meeting agenda...")

        agenda_prompt = f"""Draft a meeting agenda as a JSON array of items.

**Meeting:** {state['meeting']['title']}
**Description:** {state['meeting']['description']}
**Company:** {state['company_profile']['company_name']}
**Product:** {state['company_profile']['product_description']}
**Value Proposition:** {state['company_profile']['value_proposition']}
**Attendees:** {', '.join([a.get('name', '') for a in state['attendees']])}

{"**Insight Report Summary:** " + str(state.get('insight_report', ''))[:1000] if state['has_external'] else '**Internal meeting — focus on company context.**'}

Generate a JSON object with key "items" containing an array of agenda items:
[{{"id": "1", "text": "agenda item text", "order": 1}}, ...]
Generate 4-7 relevant, specific agenda items.
"""
        agenda_data = llm_generate_json(
            prompt=agenda_prompt,
            system_prompt="You are a meeting planning assistant. Generate structured meeting agendas in JSON.",
        )

        agenda_items = agenda_data.get("items", [])
        # Ensure proper structure
        for i, item in enumerate(agenda_items):
            if "id" not in item:
                item["id"] = str(i + 1)
            if "order" not in item:
                item["order"] = i + 1

        state["agenda_items"] = agenda_items

        await _log_workflow_step(db, mid, uid, "agenda_draft", "success",
                                  f"Drafted {len(agenda_items)} agenda items",
                                  {"item_count": len(agenda_items),
                                   "duration_ms": int((time.time() - t0) * 1000)},
                                  datetime.fromtimestamp(t0, tz=timezone.utc))

        # ─── Node 9: Validation Pass ──────────────────────────
        t0 = time.time()
        await _log_workflow_step(db, mid, uid, "validation", "started",
                                  "Validating report and agenda...")

        validation_passed = True

        # Validate report structure
        if not isinstance(state.get("insight_report"), dict):
            validation_passed = False
            logger.warning("[Workflow] Insight report is not a valid dict")

        # Validate agenda items
        for item in state.get("agenda_items", []):
            if not item.get("text") or not item.get("id"):
                validation_passed = False
                break

        state["validation_passed"] = validation_passed

        await _log_workflow_step(db, mid, uid, "validation",
                                  "success" if validation_passed else "failed",
                                  "Validation passed" if validation_passed else "Validation failed — outputs may be malformed",
                                  {"validation_passed": validation_passed,
                                   "duration_ms": int((time.time() - t0) * 1000)},
                                  datetime.fromtimestamp(t0, tz=timezone.utc))

        # ─── Node 10: Persist & Notify ────────────────────────
        t0 = time.time()
        await _log_workflow_step(db, mid, uid, "persist_notify", "started",
                                  "Saving results...")

        # Determine agenda status based on user's auto_send preference
        agenda_status = "pending_hitl"
        if user_obj.auto_send_agenda:
            agenda_status = "approved"

        # Save meeting report
        report = MeetingReport(
            id=uuid.uuid4(),
            meeting_id=mid,
            insight_report=state["insight_report"],
            handout=state["handout"],
            sources_used=state["sources_used"],
        )
        db.add(report)

        # Save agenda
        agenda = Agenda(
            id=uuid.uuid4(),
            meeting_id=mid,
            items=state["agenda_items"],
            status=agenda_status,
        )
        db.add(agenda)

        # Create checklist from agenda items
        checklist_items = [
            {
                "agenda_item_id": item["id"],
                "text": item.get("text", ""),
                "ticked_by": [],
                "comments": [],
            }
            for item in state["agenda_items"]
        ]
        checklist = ChecklistModel(
            id=uuid.uuid4(),
            meeting_id=mid,
            items=checklist_items,
            status="not_started",
        )
        db.add(checklist)

        # Update meeting status
        meeting.status = "processed"
        await db.flush()

        # Activity log
        attendee_names = ", ".join([a.get("name", "") for a in state["external_attendees"][:3]])
        activity = ActivityLog(
            id=uuid.uuid4(),
            user_id=uid,
            meeting_id=mid,
            action=f"Report generated for meeting with {attendee_names}" if attendee_names else f"Report generated for {meeting.title}",
            details={"sources_used": state["sources_used"]},
        )
        db.add(activity)

        await db.commit()

        # WebSocket notification
        await ws_manager.send_meeting_status_changed(uid, mid, "processed")

        await _log_workflow_step(db, mid, uid, "persist_notify", "success",
                                  "Results saved and notifications sent",
                                  {"agenda_status": agenda_status,
                                   "duration_ms": int((time.time() - t0) * 1000)},
                                  datetime.fromtimestamp(t0, tz=timezone.utc))
        await db.commit()

        # ─── Node 11: Agenda HITL Gate ────────────────────────
        t0 = time.time()
        if user_obj.auto_send_agenda:
            await _log_workflow_step(db, mid, uid, "agenda_hitl_gate", "started",
                                      "Auto-sending agenda (HITL bypassed)...")

            # Auto-send agenda via Google Workspace MCP
            try:
                all_attendee_emails = [
                    a["email"] for a in state["attendees"] if a.get("email") and a.get("is_external")
                ]
                if all_attendee_emails:
                    body = f"""
                    <h2>Meeting Agenda: {meeting.title}</h2>
                    <p>Scheduled: {meeting.start_time.strftime('%B %d, %Y at %I:%M %p')}</p>
                    <h3>Agenda Items:</h3>
                    <ol>
                    {''.join([f"<li>{item['text']}</li>" for item in state['agenda_items']])}
                    </ol>
                    <p><em>Sent via MeetingPilot</em></p>
                    """
                    # Send via Google Workspace MCP server
                    async with GoogleWorkspaceMCPClient(
                        access_token=user_obj.access_token or "",
                        refresh_token=user_obj.refresh_token or "",
                    ) as gws_client:
                        await gws_client.gmail_send(
                            to=", ".join(all_attendee_emails),
                            subject=f"Meeting Agenda: {meeting.title}",
                            body=body,
                        )
                    # Update agenda status to sent
                    agenda.status = "sent"
                    agenda.sent_at = datetime.now(timezone.utc)
                    await db.commit()

                await _log_workflow_step(db, mid, uid, "agenda_hitl_gate", "success",
                                          "Agenda auto-sent to all attendees",
                                          {"auto_send": True,
                                           "duration_ms": int((time.time() - t0) * 1000)},
                                          datetime.fromtimestamp(t0, tz=timezone.utc))
            except Exception as e:
                logger.error(f"[Workflow] Auto-send failed: {e}")
                await _log_workflow_step(db, mid, uid, "agenda_hitl_gate", "failed",
                                          f"Auto-send failed: {str(e)}",
                                          {"error_detail": str(e)},
                                          datetime.fromtimestamp(t0, tz=timezone.utc))
        else:
            await _log_workflow_step(db, mid, uid, "agenda_hitl_gate", "success",
                                      "Agenda waiting for human approval (HITL gate)",
                                      {"auto_send": False,
                                       "duration_ms": int((time.time() - t0) * 1000)},
                                      datetime.fromtimestamp(t0, tz=timezone.utc))

        await db.commit()

        # Final status update
        meeting.status = "processed"
        await db.commit()
        await ws_manager.send_meeting_status_changed(uid, mid, "processed")

        logger.info(f"[Workflow] Complete for meeting {mid}")

    except Exception as e:
        logger.error(f"[Workflow] Failed for meeting {mid}: {e}", exc_info=True)
        meeting.status = "failed"
        await db.commit()
        await ws_manager.send_meeting_status_changed(uid, mid, "failed")

        await _log_workflow_step(db, mid, uid, "workflow_error", "failed",
                                  f"Workflow failed: {str(e)}",
                                  {"error_detail": str(e)})
        await db.commit()
