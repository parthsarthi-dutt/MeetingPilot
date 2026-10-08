"""
Redis Queue Worker — single-consumer FIFO queue for meeting workflows.
Concurrency = 1 (deliberate v1 simplicity).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

import redis.asyncio as redis

from app.config import settings
from app.database import async_session_factory
from app.workflow.graph import run_meeting_workflow

logger = logging.getLogger(__name__)

QUEUE_KEY = "meetingpilot:workflow_queue"


async def enqueue_meeting(meeting_id: uuid.UUID, user_id: uuid.UUID):
    """Push a meeting onto the workflow queue."""
    r = redis.from_url(settings.redis_url)
    payload = json.dumps({
        "meeting_id": str(meeting_id),
        "user_id": str(user_id),
    })
    await r.rpush(QUEUE_KEY, payload)
    await r.aclose()
    logger.info(f"[Queue] Enqueued meeting {meeting_id}")


async def worker_loop():
    """
    Main worker loop — pops one job at a time from Redis (FIFO, concurrency=1).
    Runs indefinitely until cancelled.
    """
    r = redis.from_url(settings.redis_url)
    logger.info("[Worker] Started — waiting for jobs...")

    while True:
        try:
            # BLPOP blocks until a job is available (timeout=0 means wait forever)
            result = await r.blpop(QUEUE_KEY, timeout=5)
            if result is None:
                continue

            _, raw = result
            job = json.loads(raw)
            meeting_id = uuid.UUID(job["meeting_id"])
            user_id = uuid.UUID(job["user_id"])

            logger.info(f"[Worker] Processing meeting {meeting_id}")

            async with async_session_factory() as db:
                try:
                    await run_meeting_workflow(meeting_id, user_id, db)
                    logger.info(f"[Worker] Completed meeting {meeting_id}")
                except Exception as e:
                    logger.error(f"[Worker] Failed meeting {meeting_id}: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("[Worker] Shutting down...")
            break
        except Exception as e:
            logger.error(f"[Worker] Unexpected error: {e}", exc_info=True)
            await asyncio.sleep(1)

    await r.aclose()


def start_worker():
    """Entry point for the worker process."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(worker_loop())


if __name__ == "__main__":
    start_worker()
