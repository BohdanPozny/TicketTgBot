from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import User, UserRole


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Всі користувачі", callback_data="admin:users")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
        ]
    )


def admin_user_keyboard(user: User) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Кнопки зміни ролі
    roles = [
        ("👤 Клієнт", UserRole.customer),
        ("🏢 Партнер", UserRole.partner),
        ("⚙️ Адмін", UserRole.admin),
    ]
    for label, role in roles:
        if user.role != role:
            builder.row(
                InlineKeyboardButton(
                    text=f"Зробити {label}",
                    callback_data=f"admin:setrole:{user.telegram_id}:{role.value}",
                )
            )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:users"))
    return builder.as_markup()
