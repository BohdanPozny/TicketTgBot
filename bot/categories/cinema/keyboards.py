from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.config import settings
from database.models import Event


def cinema_events_keyboard(events: list[Event]) -> InlineKeyboardMarkup:
    """Список кіносеансів."""
    builder = InlineKeyboardBuilder()
    for event in events:
        builder.row(
            InlineKeyboardButton(
                text=f"🎬 {event.title} — {event.datetime.strftime('%d.%m %H:%M')}",
                callback_data=f"cinema:event:{event.id}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
    )
    return builder.as_markup()


def cinema_event_detail_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Деталі кіносеансу + кнопка відкриття Mini App."""
    webapp_url = f"{settings.webhook_url}/miniapp/cinema/customer?event_id={event_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎟 Вибрати місце",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="category:cinema")],
        ]
    )


def cinema_order_confirm_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Підтвердження замовлення з імітацією оплати."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Оплатити (тест)",
                    callback_data=f"cinema:pay:{order_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data=f"cinema:cancel:{order_id}",
                )
            ],
        ]
    )
