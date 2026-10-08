"""KBChunk model — PRD Section 5. pgvector table for RAG."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from app.database import Base


class KBChunk(Base):
    __tablename__ = "kb_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    source: Mapped[str] = mapped_column(
        Enum("gmail", "drive", "sheets", name="kb_source_enum"),
    )
    source_ref: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(384))  # sentence-transformers default dim
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="kb_chunks")
