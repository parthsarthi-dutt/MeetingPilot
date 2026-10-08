"""
Contacts routes — PATCH do-not-research.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.person_research import PersonResearch
from app.models.user import User
from app.schemas.schemas import DoNotResearchRequest

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.patch("/{person_key}/do-not-research", status_code=204)
async def set_do_not_research(
    person_key: str,
    body: DoNotResearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the do-not-research flag for a contact."""
    stmt = select(PersonResearch).where(
        PersonResearch.user_id == user.id,
        PersonResearch.person_key == person_key,
    )
    result = await db.execute(stmt)
    research = result.scalar_one_or_none()

    if research:
        research.do_not_research = body.value
    else:
        # Create a placeholder entry with the flag
        import uuid as _uuid
        research = PersonResearch(
            id=_uuid.uuid4(),
            person_key=person_key,
            user_id=user.id,
            do_not_research=body.value,
        )
        db.add(research)

    await db.commit()
