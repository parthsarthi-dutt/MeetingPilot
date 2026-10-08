import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.meeting import Meeting
from app.models.user import User
from app.services.google_workspace import calendar_get_upcoming_events
from app.worker import enqueue_meeting
from app.llm.client import extract_attendees_with_llm

logger = logging.getLogger(__name__)

async def _process_user_calendar(user: User, db: AsyncSession):
    try:
        # Run synchronous Google API call in thread pool
        events = await asyncio.to_thread(calendar_get_upcoming_events, user, 50)
        
        for event in events:
            # Skip declined events
            my_email = user.email.lower() if user.email else ""
            declined = False
            for att in event.get("attendees", []):
                if att.get("email", "").lower() == my_email and att.get("responseStatus") == "declined":
                    declined = True
                    break
            
            if declined:
                continue

            google_event_id = event.get("id")
            if not google_event_id:
                continue

            # Check if exists
            stmt = select(Meeting).where(
                Meeting.user_id == user.id, 
                Meeting.google_event_id == google_event_id
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                continue
            
            # Create new meeting
            start = event.get("start", {})
            end = event.get("end", {})
            start_str = start.get("dateTime") or start.get("date")
            end_str = end.get("dateTime") or end.get("date")
            if not start_str or not end_str:
                continue
            
            try:
                # Some all-day events just return "2023-10-01"
                if len(start_str) == 10:
                    start_dt = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    end_dt = datetime.strptime(end_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                else:
                    start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except ValueError:
                continue

            # Extract attendees using LLM (run in thread pool since it's blocking)
            title = event.get("summary", "Untitled Meeting")
            description = event.get("description", "")
            raw_attendees = event.get("attendees", [])
            my_email = user.email.lower() if user.email else ""
            
            attendees = await asyncio.to_thread(
                extract_attendees_with_llm,
                title,
                description,
                raw_attendees,
                my_email
            )
            
            meeting = Meeting(
                user_id=user.id,
                google_event_id=google_event_id,
                title=title,
                description=description,
                start_time=start_dt,
                end_time=end_dt,
                meet_link=event.get("hangoutLink") or None,
                attendees=attendees,
                status="queued",
            )
            db.add(meeting)
            await db.flush()
            
            logger.info(f"[Poller] Synced new meeting '{meeting.title}' for {user.email}")
            await enqueue_meeting(meeting.id, user.id)

        await db.commit()
    except Exception as e:
        logger.error(f"[Poller] Error processing calendar for user {user.id}: {e}", exc_info=True)
        await db.rollback()


async def calendar_poller():
    """Background task to poll Google Calendars for all users."""
    logger.info("[Poller] Calendar polling service started.")
    # Wait briefly before starting polling to allow the app to fully boot
    await asyncio.sleep(5)
    
    while True:
        try:
            async with async_session_factory() as db:
                stmt = select(User).where(User.access_token.is_not(None))
                result = await db.execute(stmt)
                users = result.scalars().all()
                
                for user in users:
                    await _process_user_calendar(user, db)
                    
        except asyncio.CancelledError:
            logger.info("[Poller] Shutting down calendar poller...")
            break
        except Exception as e:
            logger.error(f"[Poller] Unexpected error in polling loop: {e}", exc_info=True)
        
        await asyncio.sleep(60)
