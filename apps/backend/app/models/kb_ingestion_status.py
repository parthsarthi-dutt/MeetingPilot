"""KBIngestionStatus model — PRD Section 5."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class KBIngestionStatus(Base):
    __tablename__ = "kb_ingestion_status"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    status: Mapped[str] = mapped_column(
        Enum("not_started", "in_progress", "complete", name="kb_status_enum"),
        default="not_started",
    )
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    sources_included: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="kb_ingestion_status")
