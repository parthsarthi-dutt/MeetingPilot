"""
Onboarding routes — status check, company profile, KB build trigger.
"""

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.company_profile import CompanyProfile
from app.models.kb_ingestion_status import KBIngestionStatus
from app.models.user import User
from app.schemas.schemas import (
    CompanyProfileRequest,
    CompanyProfileResponse,
    OnboardingStatusResponse,
)
from app.services.kb_ingestion import build_knowledge_base

router = APIRouter(tags=["onboarding"])


@router.get("/api/onboarding/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check the current onboarding status."""
    # Company profile
    cp_stmt = select(CompanyProfile).where(CompanyProfile.user_id == user.id)
    cp_result = await db.execute(cp_stmt)
    company_profile = cp_result.scalar_one_or_none()

    # KB status
    kb_stmt = select(KBIngestionStatus).where(KBIngestionStatus.user_id == user.id)
    kb_result = await db.execute(kb_stmt)
    kb_status = kb_result.scalar_one_or_none()

    return OnboardingStatusResponse(
        permissions_complete=user.permissions_complete,
        granted_scopes=user.granted_scopes or [],
        company_profile_complete=company_profile is not None,
        kb_status=kb_status.status if kb_status else "not_started",
        kb_progress_pct=kb_status.progress_pct if kb_status else 0,
    )


@router.post("/api/company-profile", status_code=204)
async def create_company_profile(
    body: CompanyProfileRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update company profile. Triggers KB build on first creation."""
    stmt = select(CompanyProfile).where(CompanyProfile.user_id == user.id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.company_name = body.company_name
        existing.product_description = body.product_description
        existing.value_proposition = body.value_proposition
        existing.user_role_title = body.user_role_title
    else:
        profile = CompanyProfile(
            user_id=user.id,
            company_name=body.company_name,
            product_description=body.product_description,
            value_proposition=body.value_proposition,
            user_role_title=body.user_role_title,
        )
        db.add(profile)

    # Trigger KB build in background if not complete
    kb_stmt = select(KBIngestionStatus).where(KBIngestionStatus.user_id == user.id)
    kb_result = await db.execute(kb_stmt)
    kb_status = kb_result.scalar_one_or_none()

    if not kb_status or kb_status.status != "complete":
        background_tasks.add_task(_run_kb_build, user.id)

    await db.commit()


async def _run_kb_build(user_id):
    """Run KB build in background."""
    from app.database import async_session_factory
    from app.models.user import User

    async with async_session_factory() as db:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one()
        await build_knowledge_base(user, db)


@router.get("/api/company-profile", response_model=CompanyProfileResponse)
async def get_company_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current company profile."""
    stmt = select(CompanyProfile).where(CompanyProfile.user_id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Company profile not found")

    return CompanyProfileResponse(
        company_name=profile.company_name,
        product_description=profile.product_description,
        value_proposition=profile.value_proposition,
        user_role_title=profile.user_role_title,
    )
