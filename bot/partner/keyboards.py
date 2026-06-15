from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.config import settings
from database.models import Event


def partner_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Додати кіносеанс", callback_data="partner:create:cinema"),
                InlineKeyboardButton(text="➕ Додати рейс", callback_data="partner:create:bus"),
            ],
            [InlineKeyboardButton(text="📋 Мої події", callback_data="partner:events")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
        ]
    )


def partner_events_keyboard(events: list[Event]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for event in events:
        cat_emoji = "🎬" if event.category.code == "cinema" else "🚌"
        builder.row(
            InlineKeyboardButton(
                text=f"{cat_emoji} {event.title} | {event.datetime.strftime('%d.%m')}",
                callback_data=f"partner:event_stat:{event.id}",
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="partner:panel"))
    return builder.as_markup()


def partner_event_stat_keyboard(event_id: int, category_code: str) -> InlineKeyboardMarkup:
    webapp_url = (
        f"{settings.webhook_url}/miniapp/{category_code}/partner?event_id={event_id}"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗺 Редагувати схему",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="partner:events")],
        ]
    )


def partner_create_category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Кіносеанс", callback_data="partner:create:cinema"),
                InlineKeyboardButton(text="🚌 Автобусний рейс", callback_data="partner:create:bus"),
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="partner:panel")],
        ]
    )
