"""User model — PRD Section 5."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    google_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    # Encrypted at rest (application-level encryption before storage)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    granted_scopes: Mapped[dict | None] = mapped_column(JSONB, default=list)
    permissions_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    agent_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    agent_sub_toggles: Mapped[dict | None] = mapped_column(
        JSONB,
        default=lambda: {
            "osint": True,
            "agenda_auto_send": False,
            "checklist_auto_send": True,
        },
    )
    always_rerun_osint: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_send_agenda: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_send_checklist: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    company_profile = relationship("CompanyProfile", back_populates="user", uselist=False)
    credit_ledger = relationship("CreditLedger", back_populates="user", uselist=False)
    kb_ingestion_status = relationship("KBIngestionStatus", back_populates="user", uselist=False)
    meetings = relationship("Meeting", back_populates="user")
    person_researches = relationship("PersonResearch", back_populates="user")
    activity_logs = relationship("ActivityLog", back_populates="user")
    workflow_logs = relationship("WorkflowLog", back_populates="user")
    kb_chunks = relationship("KBChunk", back_populates="user")
