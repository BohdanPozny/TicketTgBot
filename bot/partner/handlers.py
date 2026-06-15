import json
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.partner.keyboards import (
    partner_create_category_keyboard,
    partner_event_stat_keyboard,
    partner_events_keyboard,
    partner_panel_keyboard,
)
from bot.common.keyboards import back_keyboard
from core.utils import format_datetime, format_price
from database.db_setup import async_session_factory
from database.models import User, UserRole
from database.repositories.events import EventRepository
from database.repositories.tickets import TicketRepository

router = Router(name="partner")


# ── FSM States ────────────────────────────────────────────────

class CreateEventState(StatesGroup):
    waiting_category = State()
    waiting_title = State()
    waiting_datetime = State()
    waiting_price = State()
    # Для автобусів — додаткові поля
    waiting_departure = State()
    waiting_arrival = State()


# ── Guard: лише партнери та адміни ───────────────────────────

def is_partner(role: UserRole) -> bool:
    return role in (UserRole.partner, UserRole.admin)


# ── Панель партнера ───────────────────────────────────────────

@router.callback_query(F.data == "partner:panel")
async def cb_partner_panel(callback: CallbackQuery, db_user: User) -> None:
    if not is_partner(db_user.role):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return
    await callback.message.edit_text(
        "🏢 <b>Панель партнера</b>\n\nОберіть дію:",
        reply_markup=partner_panel_keyboard(),
    )
    await callback.answer()


# ── Мої події ─────────────────────────────────────────────────

@router.callback_query(F.data == "partner:events")
async def cb_partner_events(callback: CallbackQuery, db_user: User) -> None:
    if not is_partner(db_user.role):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    async with async_session_factory() as session:
        repo = EventRepository(session)
        partner = await repo.get_partner_by_user_id(db_user.id)
        if not partner:
            await callback.answer("⛔ Профіль партнера не знайдено.", show_alert=True)
            return
        events = await repo.get_events_by_partner(partner.id)

    if not events:
        await callback.message.edit_text(
            "📋 У вас ще немає подій.\n\nСтворіть перший кіносеанс або рейс!",
            reply_markup=partner_panel_keyboard(),
        )
    else:
        await callback.message.edit_text(
            f"📋 <b>Ваші події</b> ({len(events)}):",
            reply_markup=partner_events_keyboard(events),
        )
    await callback.answer()


# ── Статистика події ──────────────────────────────────────────

@router.callback_query(F.data.startswith("partner:event_stat:"))
async def cb_event_stat(callback: CallbackQuery, db_user: User) -> None:
    if not is_partner(db_user.role):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    event_id = int(callback.data.split(":")[2])
    async with async_session_factory() as session:
        event_repo = EventRepository(session)
        ticket_repo = TicketRepository(session)
        event = await event_repo.get_event_by_id(event_id)
        if not event:
            await callback.answer("❌ Подію не знайдено.", show_alert=True)
            return
        stats = await ticket_repo.get_event_stats(event_id)

    revenue = stats["total_sold"] * event.base_price
    cat_emoji = "🎬" if event.category.code == "cinema" else "🚌"
    text = (
        f"{cat_emoji} <b>{event.title}</b>\n"
        f"📅 {format_datetime(event.datetime)}\n"
        f"💰 Ціна: {format_price(event.base_price)}\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"  ✅ Продано квитків: {stats['total_sold']}\n"
        f"  ☑️ Використано: {stats['used']}\n"
        f"  🔍 Очікує верифікації: {stats['pending_verification']}\n"
        f"  💵 Загальна сума: {format_price(revenue)}"
    )
    await callback.message.edit_text(
        text, reply_markup=partner_event_stat_keyboard(event_id, event.category.code)
    )
    await callback.answer()


# ── Створення події ───────────────────────────────────────────

@router.callback_query(F.data.startswith("partner:create:"))
async def cb_partner_create(callback: CallbackQuery, db_user: User, state: FSMContext) -> None:
    if not is_partner(db_user.role):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    category = callback.data.split(":")[2]  # "cinema" or "bus"
    await state.update_data(category=category)

    cat_label = "кіносеансу 🎬" if category == "cinema" else "автобусного рейсу 🚌"

    if category == "bus":
        await state.set_state(CreateEventState.waiting_departure)
        await callback.message.edit_text(
            f"➕ <b>Створення {cat_label}</b>\n\n"
            "Введіть місто відправлення:"
        )
    else:
        await state.set_state(CreateEventState.waiting_title)
        await callback.message.edit_text(
            f"➕ <b>Створення {cat_label}</b>\n\n"
            "Введіть назву фільму:"
        )
    await callback.answer()


@router.message(CreateEventState.waiting_departure)
async def fsm_bus_departure(message: Message, state: FSMContext) -> None:
    await state.update_data(departure=message.text.strip())
    await state.set_state(CreateEventState.waiting_arrival)
    await message.answer("Введіть місто прибуття:")


@router.message(CreateEventState.waiting_arrival)
async def fsm_bus_arrival(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    dep = data.get("departure", "")
    arr = message.text.strip()
    await state.update_data(
        arrival=arr,
        title=f"{dep} → {arr}",
    )
    await state.set_state(CreateEventState.waiting_datetime)
    await message.answer(
        f"Маршрут: <b>{dep} → {arr}</b>\n\n"
        "Введіть дату та час відправлення у форматі:\n"
        "<code>ДД.ММ.РРРР ГГ:ХХ</code>"
    )


@router.message(CreateEventState.waiting_title)
async def fsm_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateEventState.waiting_datetime)
    await message.answer(
        "Введіть дату та час у форматі:\n<code>ДД.ММ.РРРР ГГ:ХХ</code>"
    )


@router.message(CreateEventState.waiting_datetime)
async def fsm_datetime(message: Message, state: FSMContext) -> None:
    try:
        dt = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer(
            "❌ Невірний формат. Введіть дату у форматі:\n<code>ДД.ММ.РРРР ГГ:ХХ</code>"
        )
        return
    await state.update_data(event_datetime=dt.isoformat())
    await state.set_state(CreateEventState.waiting_price)
    await message.answer("Введіть ціну квитка (числом, грн):")


@router.message(CreateEventState.waiting_price)
async def fsm_price(message: Message, db_user: User, state: FSMContext) -> None:
    try:
        price = float(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введіть коректну ціну (наприклад: 150 або 99.50)")
        return

    data = await state.get_data()
    await state.clear()

    title = data["title"]
    category = data["category"]
    dt = datetime.fromisoformat(data["event_datetime"])

    layout_config: dict = {"category": category}
    if category == "bus":
        layout_config["departure_city"] = data.get("departure", "")
        layout_config["arrival_city"] = data.get("arrival", "")
        layout_config["total_seats"] = 40  # Дефолт; партнер змінить у Mini App

    async with async_session_factory() as session:
        repo = EventRepository(session)
        partner, _ = await repo.get_or_create_partner(db_user.id)
        cat = await repo.get_category_by_code(category)
        if not cat:
            await message.answer("❌ Категорія не знайдена. Зверніться до адміністратора.")
            return
        event = await repo.create_event(
            partner_id=partner.id,
            category_id=cat.id,
            title=title,
            event_datetime=dt,
            base_price=price,
            layout_config=layout_config,
        )
        await session.commit()
        event_id = event.id

    cat_emoji = "🎬" if category == "cinema" else "🚌"
    await message.answer(
        f"✅ <b>Подію створено!</b>\n\n"
        f"{cat_emoji} <b>{title}</b>\n"
        f"📅 {format_datetime(dt)}\n"
        f"💰 {format_price(price)}\n\n"
        "Тепер налаштуйте схему місць через панель партнера.",
        reply_markup=partner_event_stat_keyboard(event_id, category),
    )
