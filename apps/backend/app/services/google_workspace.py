"""
Google Workspace service — uses user's OAuth tokens for all Google API calls.
No separate API key needed; everything flows from the single SSO consent.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build as google_build
from tenacity import retry, stop_after_attempt, wait_exponential

from app.auth.oauth import get_google_credentials
from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


def _refresh_credentials(creds: Credentials) -> Credentials:
    """Refresh credentials if expired."""
    if creds.expired and creds.refresh_token:
        request = google.auth.transport.requests.Request()
        creds.refresh(request)
    return creds


# ─── Gmail ────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def gmail_search(user: User, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """Search Gmail for messages matching a query. Returns snippets."""
    creds = _refresh_credentials(get_google_credentials(user))
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

    return snippets


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def gmail_send(
    user: User,
    to: str | List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
) -> dict:
    """Send an email via Gmail on behalf of the user."""
    creds = _refresh_credentials(get_google_credentials(user))
    service = google_build("gmail", "v1", credentials=creds)

    if isinstance(to, list):
        to = ", ".join(to)

    message = MIMEText(body, "html")
    message["to"] = to
    message["subject"] = subject
    if cc:
        message["cc"] = ", ".join(cc)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()

    logger.info(f"[Gmail] Sent email to {to}: {subject}")
    return sent


# ─── Calendar ─────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def calendar_get_upcoming_events(user: User, max_results: int = 50) -> List[Dict[str, Any]]:
    """Fetch upcoming events from the user's primary Google Calendar."""
    creds = _refresh_credentials(get_google_credentials(user))
    service = google_build("calendar", "v3", credentials=creds)

    # Fetch events from 2 days ago to the next 30 days
    now = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    time_max = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    
    events_result = service.events().list(
        calendarId="primary", 
        timeMin=now,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True, 
        orderBy="startTime",
    ).execute()

    return events_result.get("items", [])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def calendar_create_event(
    user: User,
    summary: str,
    start_time: datetime,
    end_time: datetime,
    attendees: List[Dict[str, str]],
    description: str = "",
) -> dict:
    """Create a Google Calendar event."""
    creds = _refresh_credentials(get_google_credentials(user))
    service = google_build("calendar", "v3", credentials=creds)

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
        "attendees": [{"email": a.get("email", "")} for a in attendees if a.get("email")],
        "conferenceData": {
            "createRequest": {"requestId": f"mp-{start_time.timestamp()}"}
        },
    }

    created = service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1,
        sendUpdates="all",
    ).execute()

    logger.info(f"[Calendar] Created event: {created.get('id')}")
    return created


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def calendar_cancel_event(user: User, event_id: str):
    """Cancel a Google Calendar event."""
    creds = _refresh_credentials(get_google_credentials(user))
    service = google_build("calendar", "v3", credentials=creds)

    service.events().delete(
        calendarId="primary", eventId=event_id, sendUpdates="all"
    ).execute()
    logger.info(f"[Calendar] Cancelled event: {event_id}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def calendar_watch(user: User, webhook_url: str, channel_id: str) -> dict:
    """Set up push notifications for calendar changes."""
    creds = _refresh_credentials(get_google_credentials(user))
    service = google_build("calendar", "v3", credentials=creds)

    body = {
        "id": channel_id,
        "type": "web_hook",
        "address": webhook_url,
    }

    result = service.events().watch(calendarId="primary", body=body).execute()
    logger.info(f"[Calendar] Watch registered: {result.get('resourceId')}")
    return result


# ─── Drive ────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def drive_search(user: User, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """Search Google Drive for files matching a query."""
    creds = _refresh_credentials(get_google_credentials(user))
    service = google_build("drive", "v3", credentials=creds)

    results = service.files().list(
        q=f"fullText contains '{query}'",
        pageSize=max_results,
        fields="files(id, name, mimeType, modifiedTime, webViewLink)",
    ).execute()

    files = results.get("files", [])
    return [
        {
            "id": f["id"],
            "name": f["name"],
            "mimeType": f["mimeType"],
            "modifiedTime": f.get("modifiedTime"),
            "url": f.get("webViewLink"),
        }
        for f in files
    ]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def drive_get_file_content(user: User, file_id: str) -> str:
    """Get the text content of a Google Drive file (Docs/text)."""
    creds = _refresh_credentials(get_google_credentials(user))
    service = google_build("drive", "v3", credentials=creds)

    try:
        content = service.files().export(
            fileId=file_id, mimeType="text/plain"
        ).execute()
        text = content.decode("utf-8") if isinstance(content, bytes) else str(content)
        return text.replace("\x00", "")
    except Exception:
        # Not a Google Doc, try downloading
        content = service.files().get_media(fileId=file_id).execute()
        text = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else str(content)
        return text.replace("\x00", "")


# ─── Sheets ───────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def sheets_search(user: User, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search for spreadsheets and retrieve their content."""
    # First find spreadsheets via Drive
    files = drive_search(user, query, max_results)
    sheet_files = [f for f in files if "spreadsheet" in f.get("mimeType", "")]

    creds = _refresh_credentials(get_google_credentials(user))
    service = google_build("sheets", "v4", credentials=creds)

    results = []
    for f in sheet_files[:max_results]:
        try:
            sheet = service.spreadsheets().get(
                spreadsheetId=f["id"], includeGridData=False
            ).execute()
            sheets = sheet.get("sheets", [])
            first_sheet = sheets[0]["properties"]["title"] if sheets else "Sheet1"

            values = service.spreadsheets().values().get(
                spreadsheetId=f["id"],
                range=f"{first_sheet}!A1:Z50",
            ).execute()

            rows = values.get("values", [])
            text = "\n".join(["\t".join(row) for row in rows[:50]])

            results.append({
                "id": f["id"],
                "name": f["name"],
                "content": text[:2000],
                "url": f.get("url"),
            })
        except Exception as e:
            logger.warning(f"[Sheets] Error reading {f['id']}: {e}")

    return results
