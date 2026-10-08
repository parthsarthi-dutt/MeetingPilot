"""Checklist model — PRD Section 5."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Checklist(Base):
    __tablename__ = "checklists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id"), unique=True
    )
    items: Mapped[dict | None] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(
        Enum(
            "not_started",
            "in_progress",
            "ready_to_send",
            "sent",
            name="checklist_status_enum",
        ),
        default="not_started",
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    meeting = relationship("Meeting", back_populates="checklist")
