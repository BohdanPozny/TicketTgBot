from aiogram.types import Update
from fastapi import APIRouter, HTTPException, Request

from bot.loader import bot, dp
from core.config import settings

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("")
async def telegram_webhook(request: Request) -> dict:
    """
    Telegram webhook endpoint.
    Отримує оновлення від Telegram і передає їх у aiogram dispatcher.
    """
    body = await request.body()
    update = Update.model_validate_json(body)
    await dp.feed_update(bot=bot, update=update)
    return {"ok": True}
