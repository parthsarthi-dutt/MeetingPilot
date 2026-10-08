import asyncio
import time
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models.user import User
from sqlalchemy.pool import NullPool

async def test_engine(name, engine):
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    start = time.time()
    async with Session() as db:
        await db.execute(select(User).limit(1))
    t1 = time.time() - start
    
    start = time.time()
    async with Session() as db:
        await db.execute(select(User).limit(1))
    t2 = time.time() - start
    
    print(f"{name}: First query: {t1:.2f}s, Second query: {t2:.2f}s")
    await engine.dispose()

async def main():
    # 1. Default engine
    e1 = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )
    await test_engine("Default", e1)
    
    # 2. Statement Cache 0
    e2 = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        connect_args={"prepared_statement_cache_size": 0}
    )
    await test_engine("Statement Cache 0", e2)
    
    # 3. NullPool
    e3 = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
        connect_args={"prepared_statement_cache_size": 0}
    )
    await test_engine("NullPool", e3)

if __name__ == "__main__":
    asyncio.run(main())
