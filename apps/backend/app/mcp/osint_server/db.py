"""
OSINT MCP Server — Database helpers.

Provides async database access for the MCP server process.
The server needs its own engine because it runs as a separate process
from the main FastAPI application.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class MCPBase(DeclarativeBase):
    """Minimal base — mirrors the main app's models for the tables we need."""
    pass


class PersonResearch(MCPBase):
    """Mirror of app.models.person_research for MCP server use."""
    __tablename__ = "person_research"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_key: Mapped[str] = mapped_column(Text, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    osint_data: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    credit_charged: Mapped[bool] = mapped_column(Boolean, default=False)
    do_not_research: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CreditLedger(MCPBase):
    """Mirror of app.models.credit_ledger for MCP server use."""
    __tablename__ = "credit_ledger"

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    total_allowed: Mapped[int] = mapped_column(Integer, default=2)
    used_count: Mapped[int] = mapped_column(Integer, default=0)


class MCPDatabase:
    """
    Database manager for the OSINT MCP server.
    Creates its own async engine — independent of the main app process.
    """

    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, echo=False, pool_size=5)
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def get_session(self) -> AsyncSession:
        return self.session_factory()

    async def get_person_research(
        self, user_id: uuid.UUID, person_key: str
    ) -> Optional[PersonResearch]:
        """Look up cached person research."""
        async with self.session_factory() as session:
            stmt = select(PersonResearch).where(
                PersonResearch.user_id == user_id,
                PersonResearch.person_key == person_key,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def save_person_research(
        self,
        user_id: uuid.UUID,
        person_key: str,
        osint_data: dict,
        credit_charged: bool,
    ) -> None:
        """Store or update person research result."""
        async with self.session_factory() as session:
            stmt = select(PersonResearch).where(
                PersonResearch.user_id == user_id,
                PersonResearch.person_key == person_key,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.osint_data = osint_data
                existing.credit_charged = credit_charged
                existing.created_at = datetime.now(timezone.utc)
            else:
                new = PersonResearch(
                    id=uuid.uuid4(),
                    person_key=person_key,
                    user_id=user_id,
                    osint_data=osint_data,
                    credit_charged=credit_charged,
                )
                session.add(new)

            await session.commit()

    async def get_credits(self, user_id: uuid.UUID) -> tuple[int, int]:
        """Returns (used_count, total_allowed) for a user."""
        async with self.session_factory() as session:
            stmt = select(CreditLedger).where(CreditLedger.user_id == user_id)
            result = await session.execute(stmt)
            ledger = result.scalar_one_or_none()

            if not ledger:
                # Initialize ledger
                ledger = CreditLedger(user_id=user_id, total_allowed=2, used_count=0)
                session.add(ledger)
                await session.commit()
                return 0, 2

            return ledger.used_count, ledger.total_allowed

    async def increment_credits(self, user_id: uuid.UUID) -> None:
        """Increment used_count by 1."""
        async with self.session_factory() as session:
            stmt = select(CreditLedger).where(CreditLedger.user_id == user_id)
            result = await session.execute(stmt)
            ledger = result.scalar_one_or_none()

            if ledger:
                ledger.used_count += 1
                await session.commit()

    async def close(self):
        await self.engine.dispose()
