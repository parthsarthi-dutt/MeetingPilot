"""Meeting model — PRD Section 5."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    google_event_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    meet_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attendees: Mapped[dict | None] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(
        Enum(
            "not_processed",
            "queued",
            "processing",
            "processed",
            "done",
            "rescheduled",
            "failed",
            name="meeting_status_enum",
        ),
        default="not_processed",
        index=True,
    )
    workflow_mode: Mapped[str] = mapped_column(
        Enum("reuse", "fresh", name="workflow_mode_enum"),
        default="reuse",
    )
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    rescheduled_from_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=True
    )
    rescheduled_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="meetings")
    report = relationship("MeetingReport", back_populates="meeting", uselist=False)
    agenda = relationship("Agenda", back_populates="meeting", uselist=False)
    checklist = relationship("Checklist", back_populates="meeting", uselist=False)
    activity_logs = relationship("ActivityLog", back_populates="meeting")
    workflow_logs = relationship("WorkflowLog", back_populates="meeting")
