import asyncio
from sqlalchemy import select
from app.database import async_session_factory
from app.models.user import User
from datetime import datetime, timezone, timedelta
from app.auth.oauth import get_google_credentials
from app.services.google_workspace import _refresh_credentials
from googleapiclient.discovery import build

async def main():
    async with async_session_factory() as db:
        user = (await db.execute(select(User).where(User.access_token.is_not(None)))).scalars().first()
        if user:
            print("User:", user.email)
            creds = _refresh_credentials(get_google_credentials(user))
            service = build("calendar", "v3", credentials=creds)
            now = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            events_result = service.events().list(
                calendarId="primary",
                timeMin="2026-07-20T00:00:00Z",
                timeMax="2026-07-25T00:00:00Z",
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            events = events_result.get("items", [])
            print(f"Found {len(events)} events between July 20 and July 25, 2026.")
            for e in events:
                print("Event:", e.get("summary"), e.get("start"))
        else:
            print("No user found")

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
