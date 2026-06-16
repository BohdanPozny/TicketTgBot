import asyncio
from contextlib import suppress

from bot.loader import bot, dp, setup_routers
from database.db_setup import create_tables
from database.repositories.events import EventRepository
from database.db_setup import async_session_factory
from core.config import settings
from services.verification_service import VerificationService


async def seed_categories():
    async with async_session_factory() as session:
        repo = EventRepository(session)
        categories = await repo.get_all_categories()
        if not categories:
            await repo.create_category("Кіно", "cinema", "🎬")
            await repo.create_category("Автобуси", "bus", "🚌")
            await session.commit()


async def main():
    setup_routers()
    if settings.database_auto_create_tables:
        await create_tables()
    await seed_categories()
    await bot.delete_webhook(drop_pending_updates=True)
    verification_task = asyncio.create_task(expire_verifications_loop())
    try:
        await dp.start_polling(bot)
    finally:
        verification_task.cancel()
        with suppress(asyncio.CancelledError):
            await verification_task


async def expire_verifications_loop():
    while True:
        await asyncio.sleep(30)
        async with async_session_factory() as session:
            service = VerificationService(session)
            await service.expire_stale_verifications()
            await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
