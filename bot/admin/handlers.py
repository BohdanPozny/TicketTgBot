from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.admin.keyboards import admin_panel_keyboard, admin_user_keyboard, admin_users_keyboard
from bot.common.keyboards import back_keyboard
from core.config import settings
from database.db_setup import async_session_factory
from database.models import User, UserRole
from database.repositories.users import UserRepository

router = Router(name="admin")


def is_admin(db_user: User) -> bool:
    return db_user.role == UserRole.admin or db_user.telegram_id in settings.admin_ids


@router.callback_query(F.data == "admin:panel")
async def cb_admin_panel(callback: CallbackQuery, db_user: User) -> None:
    if not is_admin(db_user):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return
    await callback.message.edit_text(
        "⚙️ <b>Адмін-панель</b>\n\nОберіть дію:",
        reply_markup=admin_panel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:users")
async def cb_admin_users(callback: CallbackQuery, db_user: User) -> None:
    if not is_admin(db_user):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    async with async_session_factory() as session:
        repo = UserRepository(session)
        users = await repo.get_all()

    await callback.message.edit_text(
        f"👥 <b>Всі користувачі</b> ({len(users)})\n\nОберіть користувача:",
        reply_markup=admin_users_keyboard(users),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:"))
async def cb_admin_user(callback: CallbackQuery, db_user: User) -> None:
    if not is_admin(db_user):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    target_telegram_id = int(callback.data.split(":")[2])
    async with async_session_factory() as session:
        repo = UserRepository(session)
        target = await repo.get_by_telegram_id(target_telegram_id)

    if not target:
        await callback.answer("❌ Користувача не знайдено.", show_alert=True)
        return

    name = target.username or target.first_name or str(target.telegram_id)
    await callback.message.edit_text(
        f"👤 <b>{name}</b>\n"
        f"Telegram ID: <code>{target.telegram_id}</code>\n"
        f"Поточна роль: <b>{target.role.value}</b>",
        reply_markup=admin_user_keyboard(target),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery, db_user: User) -> None:
    if not is_admin(db_user):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    async with async_session_factory() as session:
        repo = UserRepository(session)
        users = await repo.get_all()

    customers = sum(1 for u in users if u.role == UserRole.customer)
    partners = sum(1 for u in users if u.role == UserRole.partner)
    admins = sum(1 for u in users if u.role == UserRole.admin)

    await callback.message.edit_text(
        f"📊 <b>Статистика системи</b>\n\n"
        f"👥 Всього користувачів: <b>{len(users)}</b>\n"
        f"  👤 Клієнтів: {customers}\n"
        f"  🏢 Партнерів: {partners}\n"
        f"  ⚙️ Адмінів: {admins}",
        reply_markup=back_keyboard("admin:panel"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:setrole:"))
async def cb_set_role(callback: CallbackQuery, db_user: User) -> None:
    if not is_admin(db_user):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    parts = callback.data.split(":")
    target_telegram_id = int(parts[2])
    new_role = UserRole(parts[3])

    async with async_session_factory() as session:
        repo = UserRepository(session)
        target = await repo.set_role(target_telegram_id, new_role)
        await session.commit()

    if target:
        name = target.username or target.first_name or str(target_telegram_id)
        await callback.message.edit_text(
            f"👤 <b>{name}</b>\n"
            f"Telegram ID: <code>{target.telegram_id}</code>\n"
            f"Поточна роль: <b>{target.role.value}</b>",
            reply_markup=admin_user_keyboard(target),
        )
        await callback.answer(f"✅ Роль змінено на {new_role.value}", show_alert=True)
    else:
        await callback.answer("❌ Користувача не знайдено.", show_alert=True)
