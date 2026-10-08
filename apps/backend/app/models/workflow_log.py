"""WorkflowLog model — PRD Section 5 & 19."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WorkflowLog(Base):
    __tablename__ = "workflow_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id"), index=True
    )
    # Denormalized so admin analytics can query across all users without joining through meetings
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    node_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Enum(
            "started",
            "success",
            "skipped",
            "failed",
            "retried",
            name="workflow_log_status_enum",
        ),
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, default=dict
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    meeting = relationship("Meeting", back_populates="workflow_logs")
    user = relationship("User", back_populates="workflow_logs")
