"""
Google OAuth 2.0 flow handler.
Single SSO consent screen — all scopes requested at once.
Uses the user's refresh_token for all subsequent Google API calls
(Gmail, Calendar, Drive, Sheets) so the user never needs a separate API key.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.models.credit_ledger import CreditLedger
from app.models.kb_ingestion_status import KBIngestionStatus


def build_oauth_flow() -> Flow:
    """Create a Google OAuth flow with all required scopes."""
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri],
            }
        },
        scopes=settings.google_scopes,
    )
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def get_authorization_url() -> tuple[str, str]:
    """
    Generate the Google consent URL.
    Returns (url, state) — state is CSRF protection.
    """
    flow = build_oauth_flow()
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url, state


async def handle_oauth_callback(
    code: str, db: AsyncSession
) -> tuple[User, list[str]]:
    """
    Exchange auth code for tokens, upsert User, initialise CreditLedger
    and KBIngestionStatus rows.
    Returns (user, granted_scopes).
    """
    flow = build_oauth_flow()
    flow.fetch_token(code=code)
    credentials: Credentials = flow.credentials

    # Fetch user profile from Google
    import google.auth.transport.requests
    from googleapiclient.discovery import build as google_build

    authed_session = google.auth.transport.requests.Request()
    credentials.refresh(authed_session)

    service = google_build("oauth2", "v2", credentials=credentials)
    user_info = service.userinfo().get().execute()

    google_id = user_info["id"]
    email = user_info["email"]
    granted_scopes = list(credentials.scopes) if credentials.scopes else []

    # Determine if all requested scopes were granted
    requested = set(settings.google_scopes)
    granted_set = set(granted_scopes)
    permissions_complete = requested.issubset(granted_set)

    # Upsert user
    stmt = select(User).where(User.google_id == google_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=uuid.uuid4(),
            google_id=google_id,
            email=email,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            granted_scopes=granted_scopes,
            permissions_complete=permissions_complete,
        )
        db.add(user)
        await db.flush()

        # Initialise credit ledger
        ledger = CreditLedger(user_id=user.id, total_allowed=2, used_count=0)
        db.add(ledger)

        # Initialise KB ingestion status
        kb_status = KBIngestionStatus(
            user_id=user.id,
            status="not_started",
            progress_pct=0,
        )
        db.add(kb_status)
    else:
        user.access_token = credentials.token
        if credentials.refresh_token:
            user.refresh_token = credentials.refresh_token
        user.granted_scopes = granted_scopes
        user.permissions_complete = permissions_complete

    await db.commit()
    await db.refresh(user)
    return user, granted_scopes


def get_google_credentials(user: User) -> Credentials:
    """
    Build Google Credentials from a User's stored tokens.
    Used by all Google Workspace service calls (Gmail, Calendar, Drive, Sheets).
    """
    return Credentials(
        token=user.access_token,
        refresh_token=user.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=user.granted_scopes or settings.google_scopes,
    )
