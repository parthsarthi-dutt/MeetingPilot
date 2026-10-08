import asyncio
from app.database import async_session_factory
from app.models.user import User
from app.mcp.osint_server.db import CreditLedger
from sqlalchemy import select

async def main():
    async with async_session_factory() as db:
        # Get the user first to get their UUID
        user_result = await db.execute(select(User).where(User.email == 'awesome.abhi83@gmail.com'))
        user = user_result.scalars().first()
        if not user:
            print("User not found")
            return
            
        print(f"User UUID: {user.id}")
        
        # Now update their CreditLedger
        ledger_result = await db.execute(select(CreditLedger).where(CreditLedger.user_id == user.id))
        ledger = ledger_result.scalars().first()
        
        if ledger:
            print(f"Current OSINT quota: {ledger.used_count}/{ledger.total_allowed}")
            ledger.total_allowed = 10
            await db.commit()
            print(f"Updated OSINT quota: {ledger.used_count}/{ledger.total_allowed}")
        else:
            print("Ledger not found, creating one...")
            ledger = CreditLedger(user_id=user.id, total_allowed=10, used_count=0)
            db.add(ledger)
            await db.commit()
            print(f"Created new OSINT quota: {ledger.used_count}/{ledger.total_allowed}")

if __name__ == "__main__":
    asyncio.run(main())
