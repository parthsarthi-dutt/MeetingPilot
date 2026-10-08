"""
Settings routes — GET, PATCH, connections, reconnect-google.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.oauth import get_authorization_url
from app.database import get_db
from app.models.user import User
from app.schemas.schemas import (
    ConnectionsResponse,
    ReconnectGoogleResponse,
    SettingsPatchRequest,
    SettingsResponse,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


from sqlalchemy import select
from app.config import settings as app_settings
from app.models.company_profile import CompanyProfile
from app.schemas.schemas import CompanyProfileResponse

@router.get("", response_model=SettingsResponse)
async def get_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user settings."""
    stmt = select(CompanyProfile).where(CompanyProfile.user_id == user.id)
    result = await db.execute(stmt)
    cp = result.scalar_one_or_none()
    
    cp_resp = None
    if cp:
        cp_resp = CompanyProfileResponse(
            company_name=cp.company_name,
            product_description=cp.product_description,
            value_proposition=cp.value_proposition,
            user_role_title=cp.user_role_title,
        )

    return SettingsResponse(
        agent_enabled=user.agent_enabled,
        agent_sub_toggles=user.agent_sub_toggles or {},
        auto_send_agenda=user.auto_send_agenda,
        always_rerun_osint=user.always_rerun_osint,
        auto_send_checklist=user.auto_send_checklist,
        is_admin=(user.email == app_settings.admin_email),
        company_profile=cp_resp,
    )


@router.patch("", status_code=204)
async def update_settings(
    body: SettingsPatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partial update of user settings."""
    if body.agent_enabled is not None:
        user.agent_enabled = body.agent_enabled
    if body.agent_sub_toggles is not None:
        user.agent_sub_toggles = body.agent_sub_toggles
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, "agent_sub_toggles")
    if body.auto_send_agenda is not None:
        user.auto_send_agenda = body.auto_send_agenda
    if body.always_rerun_osint is not None:
        user.always_rerun_osint = body.always_rerun_osint
    if body.auto_send_checklist is not None:
        user.auto_send_checklist = body.auto_send_checklist

    if body.company_profile:
        stmt = select(CompanyProfile).where(CompanyProfile.user_id == user.id)
        result = await db.execute(stmt)
        cp = result.scalar_one_or_none()
        if cp:
            if body.company_profile.company_name is not None:
                cp.company_name = body.company_profile.company_name
            if body.company_profile.product_description is not None:
                cp.product_description = body.company_profile.product_description
            if body.company_profile.value_proposition is not None:
                cp.value_proposition = body.company_profile.value_proposition
            if body.company_profile.user_role_title is not None:
                cp.user_role_title = body.company_profile.user_role_title

    await db.commit()


@router.get("/connections", response_model=ConnectionsResponse)
async def get_connections(
    user: User = Depends(get_current_user),
):
    """Get currently granted Google scopes."""
    return ConnectionsResponse(
        granted_scopes=user.granted_scopes or [],
        permissions_complete=user.permissions_complete,
    )


@router.post("/reconnect-google", response_model=ReconnectGoogleResponse)
async def reconnect_google():
    """Re-trigger Google OAuth to grant additional scopes."""
    url, _ = get_authorization_url()
    return ReconnectGoogleResponse(redirect_url=url)
