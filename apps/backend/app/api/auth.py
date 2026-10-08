"""
Auth routes — Google OAuth flow endpoints.
"""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import create_access_token
from app.auth.oauth import get_authorization_url, handle_oauth_callback
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/login")
async def login():
    """Redirect to Google OAuth consent screen (single SSO, all scopes)."""
    url, state = get_authorization_url()
    return RedirectResponse(url=url)


@router.get("/callback")
async def callback(
    code: str,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth callback — exchange code for tokens, create/update user,
    return JWT access token.
    """
    user, granted_scopes = await handle_oauth_callback(code, db)

    token = create_access_token(str(user.id), user.email)

    # Redirect to frontend with token
    redirect_url = f"{settings.frontend_url}/auth/callback?token={token}"
    return RedirectResponse(url=redirect_url)
