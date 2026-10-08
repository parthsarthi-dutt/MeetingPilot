import asyncio
from sqlalchemy import select
from app.database import async_session_factory
from app.models.meeting import Meeting

async def main():
    async with async_session_factory() as db:
        stmt = select(Meeting.title, Meeting.meet_link, Meeting.start_time)
        result = await db.execute(stmt)
        print('-'*100)
        print(f'{"Title":<35} | {"Meet Link":<35} | {"Start Time"}')
        print('-'*100)
        for title, link, st in result:
            title_trunc = (title[:33] if title else '')
            link_trunc = (str(link)[:33] if link else 'None')
            print(f'{title_trunc:<35} | {link_trunc:<35} | {st}')
        print('-'*100)

asyncio.run(main())
