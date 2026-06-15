import asyncio
from bot.loader import bot, dp, setup_routers
from database.db_setup import create_tables
from database.repositories.events import EventRepository
from database.db_setup import async_session_factory


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
    await create_tables()
    await seed_categories()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
