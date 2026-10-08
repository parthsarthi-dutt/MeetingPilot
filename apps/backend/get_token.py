import asyncio
from app.auth.dependencies import create_access_token
from app.database import async_session_factory
from app.models.user import User
from sqlalchemy import select

async def main():
    async with async_session_factory() as db:
        result = await db.execute(select(User))
        user = result.scalars().first()
        if user:
            print(create_access_token(user_id=str(user.id), email=user.email))

asyncio.run(main())
