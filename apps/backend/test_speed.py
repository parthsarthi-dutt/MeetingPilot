import asyncio
import time
import httpx
from app.database import async_session_factory
from app.auth.dependencies import create_access_token
from app.models.user import User
from sqlalchemy import select

async def main():
    async with async_session_factory() as db:
        user_result = await db.execute(select(User).where(User.email == 'awesome.abhi83@gmail.com'))
        user = user_result.scalars().first()
    
    if not user:
        return
        
    token = create_access_token(str(user.id), user.email)
    
    start = time.time()
    async with httpx.AsyncClient() as client:
        r = await client.get('http://localhost:8000/api/admin/analytics/overview', headers={"Authorization": f"Bearer {token}"})
    print(f"/api/admin/analytics/overview took {time.time() - start:.2f} seconds")
    
    start = time.time()
    async with httpx.AsyncClient() as client:
        r = await client.get('http://localhost:8000/api/admin/analytics/users', headers={"Authorization": f"Bearer {token}"})
    print(f"/api/admin/analytics/users took {time.time() - start:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
