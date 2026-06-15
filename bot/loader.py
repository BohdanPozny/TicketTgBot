from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from core.config import settings

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


def setup_routers() -> None:
    from bot.middlewares.role_middleware import RoleMiddleware
    from bot.common.handlers import router as common_router
    from bot.categories.cinema.handlers import router as cinema_router
    from bot.categories.bus.handlers import router as bus_router
    from bot.partner.handlers import router as partner_router
    from bot.admin.handlers import router as admin_router

    dp.message.middleware(RoleMiddleware())
    dp.callback_query.middleware(RoleMiddleware())

    dp.include_router(common_router)
    dp.include_router(partner_router)
    dp.include_router(admin_router)
    dp.include_router(cinema_router)
    dp.include_router(bus_router)
