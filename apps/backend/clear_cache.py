import asyncio
from app.database import async_session_factory
from app.mcp.osint_server.db import PersonResearch
from sqlalchemy import delete

async def main():
    async with async_session_factory() as db:
        result = await db.execute(delete(PersonResearch))
        await db.commit()
        print(f"Cleared OSINT cache!")

if __name__ == "__main__":
    asyncio.run(main())
