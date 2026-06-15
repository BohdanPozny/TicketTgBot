from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard(role: str) -> InlineKeyboardMarkup:
    """Головне меню з категоріями та опціями залежно від ролі."""
    builder = InlineKeyboardBuilder()

    # Категорії квитків (для всіх)
    builder.row(
        InlineKeyboardButton(text="🎬 Кіно", callback_data="category:cinema"),
        InlineKeyboardButton(text="🚌 Автобуси", callback_data="category:bus"),
    )

    # Мої квитки
    builder.row(
        InlineKeyboardButton(text="🎟 Мої квитки", callback_data="my_tickets")
    )

    # Панель партнера
    if role in ("partner", "admin"):
        builder.row(
            InlineKeyboardButton(text="🏢 Панель партнера", callback_data="partner:panel")
        )

    # Адмін-панель
    if role == "admin":
        builder.row(
            InlineKeyboardButton(text="⚙️ Адмін-панель", callback_data="admin:panel")
        )

    return builder.as_markup()


def back_keyboard(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Кнопка «Назад»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
        ]
    )


def confirm_cancel_keyboard(
    confirm_data: str, cancel_data: str = "main_menu"
) -> InlineKeyboardMarkup:
    """Клавіатура підтвердження/скасування."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Підтвердити", callback_data=confirm_data),
                InlineKeyboardButton(text="❌ Скасувати", callback_data=cancel_data),
            ]
        ]
    )


def ticket_verification_keyboard(verification_id: int) -> InlineKeyboardMarkup:
    """Клавіатура для підтвердження/відхилення проходу."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Підтвердити прохід",
                    callback_data=f"verify:confirm:{verification_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Відхилити",
                    callback_data=f"verify:reject:{verification_id}",
                ),
            ]
        ]
    )
