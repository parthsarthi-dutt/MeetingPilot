"""
KB Ingestion Service — one-time RAG knowledge base build at onboarding.
Pulls from Gmail, Drive, Sheets (based on granted scopes), chunks semantically,
generates embeddings, and stores in kb_chunks (pgvector).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.kb_chunk import KBChunk
from app.models.kb_ingestion_status import KBIngestionStatus
from app.models.user import User
from app.services.google_workspace import (
    gmail_search,
    drive_search,
    drive_get_file_content,
    sheets_search,
)
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

# Embedding model — loaded lazily
_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _chunk_text(text: str, max_chunk_size: int = 500) -> List[str]:
    """
    Semantic chunking by paragraph boundary.
    Splits on double newlines, then groups short paragraphs together.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) < max_chunk_size:
            current_chunk += ("\n\n" + para) if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


async def build_knowledge_base(user: User, db: AsyncSession):
    """
    Build the RAG knowledge base for a user. Called once at onboarding.
    Progress is reported via WebSocket kb_progress events.
    """
    user_id = user.id
    granted = set(user.granted_scopes or [])

    # Update status to in_progress
    stmt = select(KBIngestionStatus).where(KBIngestionStatus.user_id == user_id)
    result = await db.execute(stmt)
    kb_status = result.scalar_one_or_none()
    if not kb_status:
        kb_status = KBIngestionStatus(user_id=user_id, status="in_progress", progress_pct=0)
        db.add(kb_status)
    else:
        kb_status.status = "in_progress"
        kb_status.progress_pct = 0
    await db.commit()

    await ws_manager.send_kb_progress(user_id, 0, "in_progress")

    sources_included = {}
    total_chunks = 0
    embedder = _get_embedder()

    # Determine which sources to process
    has_gmail = "https://www.googleapis.com/auth/gmail.readonly" in granted
    has_drive = "https://www.googleapis.com/auth/drive.readonly" in granted
    has_sheets = "https://www.googleapis.com/auth/spreadsheets" in granted

    source_count = sum([has_gmail, has_drive, has_sheets])
    progress_per_source = 90 // max(source_count, 1)
    current_progress = 5

    # ─── Gmail ────────────────────────────────────────────────
    if has_gmail:
        try:
            logger.info(f"[KB] Ingesting Gmail for user {user_id}")
            messages = gmail_search(user, "in:inbox", max_results=settings.kb_gmail_limit)
            sources_included["gmail"] = True

            for msg in messages:
                content = f"Subject: {msg.get('subject', '')}\nFrom: {msg.get('from', '')}\n{msg.get('snippet', '')}"
                chunks = _chunk_text(content)
                for chunk in chunks:
                    embedding = embedder.encode(chunk).tolist()
                    kb_chunk = KBChunk(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        source="gmail",
                        source_ref=msg.get("id", ""),
                        content=chunk,
                        embedding=embedding,
                    )
                    db.add(kb_chunk)
                    total_chunks += 1

            current_progress += progress_per_source
            kb_status.progress_pct = current_progress
            await db.commit()
            await ws_manager.send_kb_progress(user_id, current_progress, "in_progress")
        except Exception as e:
            logger.error(f"[KB] Gmail ingestion error: {e}")
            sources_included["gmail"] = False

    # ─── Drive ────────────────────────────────────────────────
    if has_drive:
        try:
            logger.info(f"[KB] Ingesting Drive for user {user_id}")
            files = drive_search(user, "", max_results=settings.kb_drive_limit)
            sources_included["drive"] = True

            for f in files:
                try:
                    content = drive_get_file_content(user, f["id"])
                    chunks = _chunk_text(content)
                    for chunk in chunks:
                        embedding = embedder.encode(chunk).tolist()
                        kb_chunk = KBChunk(
                            id=uuid.uuid4(),
                            user_id=user_id,
                            source="drive",
                            source_ref=f["id"],
                            content=chunk,
                            embedding=embedding,
                        )
                        db.add(kb_chunk)
                        total_chunks += 1
                except Exception as e:
                    logger.warning(f"[KB] Drive file {f['id']} error: {e}")

            current_progress += progress_per_source
            kb_status.progress_pct = current_progress
            await db.commit()
            await ws_manager.send_kb_progress(user_id, current_progress, "in_progress")
        except Exception as e:
            logger.error(f"[KB] Drive ingestion error: {e}")
            sources_included["drive"] = False

    # ─── Sheets ───────────────────────────────────────────────
    if has_sheets:
        try:
            logger.info(f"[KB] Ingesting Sheets for user {user_id}")
            sheets = sheets_search(user, "", max_results=settings.kb_sheets_limit)
            sources_included["sheets"] = True

            for s in sheets:
                content = s.get("content", "")
                chunks = _chunk_text(content)
                for chunk in chunks:
                    embedding = embedder.encode(chunk).tolist()
                    kb_chunk = KBChunk(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        source="sheets",
                        source_ref=s["id"],
                        content=chunk,
                        embedding=embedding,
                    )
                    db.add(kb_chunk)
                    total_chunks += 1

            current_progress += progress_per_source
            kb_status.progress_pct = current_progress
            await db.commit()
            await ws_manager.send_kb_progress(user_id, current_progress, "in_progress")
        except Exception as e:
            logger.error(f"[KB] Sheets ingestion error: {e}")
            sources_included["sheets"] = False

    # ─── Finalize ─────────────────────────────────────────────
    kb_status.status = "complete"
    kb_status.progress_pct = 100
    kb_status.sources_included = sources_included
    kb_status.completed_at = datetime.now(timezone.utc)
    await db.commit()

    await ws_manager.send_kb_progress(user_id, 100, "complete")
    logger.info(f"[KB] Build complete for user {user_id}: {total_chunks} chunks indexed")
