from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.db_setup import async_session_factory
from database.repositories.users import UserRepository


class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = None
        if isinstance(event, Message) and event.from_user:
            tg_user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            tg_user = event.from_user

        if tg_user:
            async with async_session_factory() as session:
                repo = UserRepository(session)
                db_user, _ = await repo.get_or_create(
                    telegram_id=tg_user.id,
                    username=tg_user.username,
                    first_name=tg_user.first_name,
                )
                await session.commit()
                data["db_user"] = db_user
                data["user_role"] = db_user.role
                data["db_session"] = session

        return await handler(event, data)
