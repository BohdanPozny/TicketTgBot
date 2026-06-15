from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.config import settings
from database.models import Event


def bus_routes_keyboard(events: list[Event]) -> InlineKeyboardMarkup:
    """Список автобусних рейсів."""
    builder = InlineKeyboardBuilder()
    for event in events:
        config = event.layout_config or {}
        dep = config.get("departure_city", "")
        arr = config.get("arrival_city", "")
        label = f"{dep} → {arr}" if dep and arr else event.title
        builder.row(
            InlineKeyboardButton(
                text=f"🚌 {label} — {event.datetime.strftime('%d.%m %H:%M')}",
                callback_data=f"bus:event:{event.id}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
    )
    return builder.as_markup()


def bus_event_detail_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Деталі рейсу + кнопка відкриття Mini App."""
    webapp_url = f"{settings.webhook_url}/miniapp/bus/customer?event_id={event_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎟 Вибрати місце",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="category:bus")],
        ]
    )


def bus_order_confirm_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Підтвердження замовлення з імітацією оплати."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Оплатити (тест)",
                    callback_data=f"bus:pay:{order_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data=f"bus:cancel:{order_id}",
                )
            ],
        ]
    )
