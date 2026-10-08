import asyncio
import os
from sqlalchemy.future import select
from app.database import async_session_factory
from app.models.user import User
from app.mcp.client import GoogleWorkspaceMCPClient

async def main():
    async with async_session_factory() as db:
        user = (await db.execute(select(User).where(User.email == "awesome.abhi83@gmail.com"))).scalars().first()
        if not user or not user.access_token:
            print("No user or token")
            return
        
        print("Sending email...")
        async with GoogleWorkspaceMCPClient(
            access_token=user.access_token,
            refresh_token=user.refresh_token or "",
        ) as client:
            try:
                res = await client.gmail_send(
                    to="awesome.abhi83@gmail.com",
                    subject="Test from MeetingPilot",
                    body="<h1>Hello World</h1><p>Testing MCP send</p>"
                )
                print("Result:", res)
            except Exception as e:
                print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
