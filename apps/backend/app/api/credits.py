"""
Credits route — GET used/total.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.credit_ledger import CreditLedger
from app.models.user import User
from app.schemas.schemas import CreditsResponse

router = APIRouter(prefix="/api/credits", tags=["credits"])


@router.get("", response_model=CreditsResponse)
async def get_credits(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get OSINT credit usage for the current user."""
    stmt = select(CreditLedger).where(CreditLedger.user_id == user.id)
    result = await db.execute(stmt)
    ledger = result.scalar_one_or_none()

    return CreditsResponse(
        used_count=ledger.used_count if ledger else 0,
        total_allowed=ledger.total_allowed if ledger else 2,
    )
