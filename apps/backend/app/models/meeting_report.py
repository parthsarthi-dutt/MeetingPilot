"""MeetingReport model — PRD Section 5."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MeetingReport(Base):
    __tablename__ = "meeting_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id"), unique=True
    )
    insight_report: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    handout: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    sources_used: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    meeting = relationship("Meeting", back_populates="report")
