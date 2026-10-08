"""
Google Workspace MCP Server — FastMCP Server Definition.

Exposes Gmail, Calendar, Drive, and Sheets as MCP tools.
Each tool receives the user's OAuth tokens as parameters — the server
is fully stateless. Tokens are stored in the DB after SSO login and
passed through by the MCP client per call.

Run standalone:  python -m app.mcp.google_workspace
Or via FastMCP:  fastmcp run app/mcp/google_workspace/server.py
"""

import base64
import json
import logging
import os
from email.mime.text import MIMEText
from typing import Optional

import google.auth.transport.requests
from fastmcp import FastMCP
from fastmcp.server.context import Context
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build as google_build

logger = logging.getLogger(__name__)

# ─── Server ──────────────────────────────────────────────────
mcp = FastMCP("MeetingPilot Google Workspace Server")

# Client ID/secret are app-level (same for all users), loaded from env
_GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
_GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")


def _build_credentials(access_token: str, refresh_token: str) -> Credentials:
    """
    Build Google Credentials from per-user tokens.

    access_token and refresh_token are unique per user — they come from the DB
    where they were stored after the user's Google SSO login. The client_id
    and client_secret are app-level constants (same for every user).
    """
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_GOOGLE_CLIENT_ID,
        client_secret=_GOOGLE_CLIENT_SECRET,
    )
    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(google.auth.transport.requests.Request())
    return creds


# =============================================================================
# GMAIL TOOLS
# =============================================================================


@mcp.tool()
async def gmail_search(
    access_token: str,
    refresh_token: str,
    query: str,
    max_results: int = 20,
    ctx: Context = None,
) -> str:
    """
    Search Gmail messages matching a query string.

    Args:
        access_token: User's Google OAuth access token (from DB after SSO).
        refresh_token: User's Google OAuth refresh token (from DB after SSO).
        query: Gmail search query (e.g., 'from:jane@example.com' or '"John Doe"').
        max_results: Maximum number of messages to return.

    Returns:
        JSON array of message objects with id, subject, from, date, snippet.
    """
    await ctx.info(f"Searching Gmail: {query}")
    creds = _build_credentials(access_token, refresh_token)
    service = google_build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    snippets = []
    for msg_meta in messages[:max_results]:
        msg = service.users().messages().get(
            userId="me", id=msg_meta["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        snippets.append({
            "id": msg_meta["id"],
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
        })

    await ctx.info(f"Found {len(snippets)} Gmail messages")
    return json.dumps({"messages": snippets, "total": len(snippets)})


@mcp.tool()
async def gmail_send(
    access_token: str,
    refresh_token: str,
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """
    Send an email via Gmail on behalf of the authenticated user.

    Args:
        access_token: User's Google OAuth access token (from DB after SSO).
        refresh_token: User's Google OAuth refresh token (from DB after SSO).
        to: Recipient email address(es), comma-separated.
        subject: Email subject line.
        body: HTML body content.
        cc: CC recipients, comma-separated (optional).

    Returns:
        JSON object with message id and status.
    """
    await ctx.info(f"Sending email to: {to}")
    creds = _build_credentials(access_token, refresh_token)
    service = google_build("gmail", "v1", credentials=creds)

    message = MIMEText(body, "html")
    message["to"] = to
    message["subject"] = subject
    if cc:
        message["cc"] = cc

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()

    await ctx.info(f"Email sent: {sent.get('id')}")
    return json.dumps({"message_id": sent.get("id"), "status": "sent"})


# =============================================================================
# CALENDAR TOOLS
# =============================================================================


@mcp.tool()
async def calendar_create_event(
    access_token: str,
    refresh_token: str,
    summary: str,
    start_time: str,
    end_time: str,
    attendees_json: str = "[]",
    description: str = "",
    ctx: Context = None,
) -> str:
    """
    Create a Google Calendar event with optional attendees.

    Args:
        access_token: User's Google OAuth access token (from DB after SSO).
        refresh_token: User's Google OAuth refresh token (from DB after SSO).
        summary: Event title.
        start_time: ISO 8601 start datetime.
        end_time: ISO 8601 end datetime.
        attendees_json: JSON array of attendee objects with 'email' field.
        description: Event description (optional).

    Returns:
        JSON object with event id, htmlLink, and hangoutLink.
    """
    await ctx.info(f"Creating calendar event: {summary}")
    creds = _build_credentials(access_token, refresh_token)
    service = google_build("calendar", "v3", credentials=creds)

    attendees = json.loads(attendees_json) if attendees_json else []

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": "UTC"},
        "end": {"dateTime": end_time, "timeZone": "UTC"},
        "attendees": [{"email": a.get("email", "")} for a in attendees if a.get("email")],
        "conferenceData": {
            "createRequest": {"requestId": f"mp-{hash(start_time)}"}
        },
    }

    created = service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1,
        sendUpdates="all",
    ).execute()

    await ctx.info(f"Event created: {created.get('id')}")
    return json.dumps({
        "event_id": created.get("id"),
        "html_link": created.get("htmlLink"),
        "hangout_link": created.get("hangoutLink"),
    })


@mcp.tool()
async def calendar_cancel_event(
    access_token: str,
    refresh_token: str,
    event_id: str,
    ctx: Context = None,
) -> str:
    """
    Cancel (delete) a Google Calendar event.

    Args:
        access_token: User's Google OAuth access token (from DB after SSO).
        refresh_token: User's Google OAuth refresh token (from DB after SSO).
        event_id: The Google Calendar event ID to cancel.

    Returns:
        JSON object with status.
    """
    await ctx.info(f"Cancelling calendar event: {event_id}")
    creds = _build_credentials(access_token, refresh_token)
    service = google_build("calendar", "v3", credentials=creds)

    service.events().delete(
        calendarId="primary", eventId=event_id, sendUpdates="all"
    ).execute()

    await ctx.info(f"Event cancelled: {event_id}")
    return json.dumps({"event_id": event_id, "status": "cancelled"})


@mcp.tool()
async def calendar_watch(
    access_token: str,
    refresh_token: str,
    webhook_url: str,
    channel_id: str,
    ctx: Context = None,
) -> str:
    """
    Register a push notification webhook for calendar changes.

    Args:
        access_token: User's Google OAuth access token (from DB after SSO).
        refresh_token: User's Google OAuth refresh token (from DB after SSO).
        webhook_url: HTTPS URL to receive push notifications.
        channel_id: Unique ID for this watch channel.

    Returns:
        JSON object with resourceId and expiration.
    """
    await ctx.info(f"Registering calendar watch: {webhook_url}")
    creds = _build_credentials(access_token, refresh_token)
    service = google_build("calendar", "v3", credentials=creds)

    result = service.events().watch(
        calendarId="primary",
        body={"id": channel_id, "type": "web_hook", "address": webhook_url},
    ).execute()

    await ctx.info(f"Watch registered: {result.get('resourceId')}")
    return json.dumps({
        "resource_id": result.get("resourceId"),
        "expiration": result.get("expiration"),
    })


# =============================================================================
# DRIVE TOOLS
# =============================================================================


@mcp.tool()
async def drive_search(
    access_token: str,
    refresh_token: str,
    query: str,
    max_results: int = 20,
    ctx: Context = None,
) -> str:
    """
    Search Google Drive for files matching a full-text query.

    Args:
        access_token: User's Google OAuth access token (from DB after SSO).
        refresh_token: User's Google OAuth refresh token (from DB after SSO).
        query: Search text to find in file contents and names.
        max_results: Maximum number of files to return.

    Returns:
        JSON array of file objects with id, name, mimeType, modifiedTime, url.
    """
    await ctx.info(f"Searching Drive: {query}")
    creds = _build_credentials(access_token, refresh_token)
    service = google_build("drive", "v3", credentials=creds)

    q_filter = f"fullText contains '{query}'" if query else ""
    results = service.files().list(
        q=q_filter,
        pageSize=max_results,
        fields="files(id, name, mimeType, modifiedTime, webViewLink)",
    ).execute()

    files = [
        {
            "id": f["id"],
            "name": f["name"],
            "mimeType": f["mimeType"],
            "modifiedTime": f.get("modifiedTime"),
            "url": f.get("webViewLink"),
        }
        for f in results.get("files", [])
    ]

    await ctx.info(f"Found {len(files)} Drive files")
    return json.dumps({"files": files, "total": len(files)})


@mcp.tool()
async def drive_get_file_content(
    access_token: str,
    refresh_token: str,
    file_id: str,
    ctx: Context = None,
) -> str:
    """
    Get the text content of a Google Drive file.

    Args:
        access_token: User's Google OAuth access token (from DB after SSO).
        refresh_token: User's Google OAuth refresh token (from DB after SSO).
        file_id: The Google Drive file ID.

    Returns:
        JSON object with file_id and content (text).
    """
    await ctx.info(f"Reading Drive file: {file_id}")
    creds = _build_credentials(access_token, refresh_token)
    service = google_build("drive", "v3", credentials=creds)

    try:
        content = service.files().export(fileId=file_id, mimeType="text/plain").execute()
        text = content.decode("utf-8") if isinstance(content, bytes) else str(content)
    except Exception:
        content = service.files().get_media(fileId=file_id).execute()
        text = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else str(content)

    await ctx.info(f"Read {len(text)} chars from file {file_id}")
    return json.dumps({"file_id": file_id, "content": text[:10000]})


# =============================================================================
# SHEETS TOOLS
# =============================================================================


@mcp.tool()
async def sheets_search(
    access_token: str,
    refresh_token: str,
    query: str,
    max_results: int = 10,
    ctx: Context = None,
) -> str:
    """
    Search for Google Sheets and retrieve their contents.

    Args:
        access_token: User's Google OAuth access token (from DB after SSO).
        refresh_token: User's Google OAuth refresh token (from DB after SSO).
        query: Search text to find spreadsheets.
        max_results: Maximum number of spreadsheets to return.

    Returns:
        JSON array of sheet objects with id, name, content (first 50 rows).
    """
    await ctx.info(f"Searching Sheets: {query}")
    creds = _build_credentials(access_token, refresh_token)
    drive_service = google_build("drive", "v3", credentials=creds)
    sheets_service = google_build("sheets", "v4", credentials=creds)

    q_filter = f"fullText contains '{query}' and mimeType='application/vnd.google-apps.spreadsheet'"
    files_result = drive_service.files().list(
        q=q_filter, pageSize=max_results,
        fields="files(id, name, webViewLink)",
    ).execute()

    results = []
    for f in files_result.get("files", [])[:max_results]:
        try:
            sheet = sheets_service.spreadsheets().get(
                spreadsheetId=f["id"], includeGridData=False
            ).execute()
            sheets = sheet.get("sheets", [])
            first_sheet = sheets[0]["properties"]["title"] if sheets else "Sheet1"

            values = sheets_service.spreadsheets().values().get(
                spreadsheetId=f["id"], range=f"{first_sheet}!A1:Z50",
            ).execute()

            rows = values.get("values", [])
            text = "\n".join(["\t".join(row) for row in rows[:50]])

            results.append({
                "id": f["id"],
                "name": f["name"],
                "content": text[:2000],
                "url": f.get("webViewLink"),
            })
        except Exception as e:
            logger.warning(f"Error reading sheet {f['id']}: {e}")

    await ctx.info(f"Found {len(results)} Sheets")
    return json.dumps({"sheets": results, "total": len(results)})


# =============================================================================
# RESOURCES — these use env tokens because resources are read by
# the MCP Inspector / dev tools, not per-user workflow calls
# =============================================================================


@mcp.resource("google://user/profile")
async def get_user_profile() -> str:
    """Read the authenticated user's Google profile (dev/testing only)."""
    # Resources don't receive runtime args — use env for dev testing
    creds = _build_credentials(
        os.environ.get("GOOGLE_DEV_ACCESS_TOKEN", ""),
        os.environ.get("GOOGLE_DEV_REFRESH_TOKEN", ""),
    )
    service = google_build("oauth2", "v2", credentials=creds)
    info = service.userinfo().get().execute()
    return json.dumps(info)


@mcp.resource("google://calendar/upcoming")
async def get_upcoming_events() -> str:
    """Read the next 10 upcoming calendar events (dev/testing only)."""
    from datetime import datetime, timezone
    creds = _build_credentials(
        os.environ.get("GOOGLE_DEV_ACCESS_TOKEN", ""),
        os.environ.get("GOOGLE_DEV_REFRESH_TOKEN", ""),
    )
    service = google_build("calendar", "v3", credentials=creds)

    now = datetime.now(timezone.utc).isoformat()
    events_result = service.events().list(
        calendarId="primary", timeMin=now, maxResults=10,
        singleEvents=True, orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])
    return json.dumps([{
        "id": e.get("id"),
        "summary": e.get("summary"),
        "start": e.get("start", {}).get("dateTime"),
        "end": e.get("end", {}).get("dateTime"),
        "attendees": [a.get("email") for a in e.get("attendees", [])],
        "hangoutLink": e.get("hangoutLink"),
    } for e in events])


# =============================================================================
# PROMPTS
# =============================================================================


@mcp.prompt()
def email_agenda_prompt(meeting_title: str, agenda_items: str) -> str:
    """Generate a prompt for composing an agenda email."""
    return f"""Compose a professional meeting agenda email for "{meeting_title}".

Agenda items:
{agenda_items}

The email should be:
- Professional but warm
- Include all agenda items in a numbered list
- Mention approximate time allocations
- End with a positive note about the upcoming meeting"""


@mcp.prompt()
def search_context_prompt(person_name: str, company: str) -> str:
    """Generate a search query prompt for finding workspace context about a person."""
    return f"""Generate effective search queries to find relevant context about
{person_name} from {company} in the user's Gmail, Drive, and Sheets.

Consider:
- Direct email exchanges
- Documents or files mentioning this person
- Shared spreadsheets or meeting notes
- Any previous correspondence or collaboration"""


if __name__ == "__main__":
    mcp.run()

