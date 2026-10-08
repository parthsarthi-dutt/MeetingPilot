import asyncio
import httpx
from app.auth.dependencies import create_access_token
from app.database import async_session_factory
from app.models.user import User
from sqlalchemy import select

async def main():
    async with async_session_factory() as db:
        # Get first user
        result = await db.execute(select(User))
        user = result.scalars().first()
        if not user:
            print("No user found")
            return
        print(f"Using user: {user.email}")
        
        # Create token
        token = create_access_token(
            user_id=str(user.id),
            email=user.email
        )
        print(f"Token: {token}")

        # Call simulate API
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:8000/api/meetings/simulate",
                json={
                    "title": "Strategy Sync",
                    "description": "Discussing Q3 strategy and OSINT integration",
                    "start_time": "2026-07-23T15:00:00Z",
                    "end_time": "2026-07-23T16:00:00Z",
                    "attendees": [
                        {"name": "Rahul Pandey", "email": "rahul@cisco.com", "company": "Cisco"}
                    ]
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )
            print(f"Response {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    asyncio.run(main())
