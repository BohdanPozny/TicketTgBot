import json

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.categories.cinema.keyboards import (
    cinema_event_detail_keyboard,
    cinema_events_keyboard,
    cinema_order_confirm_keyboard,
)
from bot.categories.cinema.service import CinemaService
from bot.common.keyboards import back_keyboard
from core.utils import format_datetime, format_price
from database.db_setup import async_session_factory
from database.models import User
from database.repositories.orders import OrderRepository
from services.payment_service import PaymentService
from services.ticket_service import TicketService

router = Router(name="cinema")


@router.callback_query(F.data == "category:cinema")
async def cb_cinema_list(callback: CallbackQuery, db_user: User) -> None:
    async with async_session_factory() as session:
        svc = CinemaService(session)
        events = await svc.get_active_sessions()
        text = await svc.format_event_list(events)

    if events:
        await callback.message.edit_text(text, reply_markup=cinema_events_keyboard(events))
    else:
        await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("cinema:event:"))
async def cb_cinema_event(callback: CallbackQuery, db_user: User) -> None:
    event_id = int(callback.data.split(":")[2])
    async with async_session_factory() as session:
        svc = CinemaService(session)
        event = await svc.get_event(event_id)

    if not event:
        await callback.answer("❌ Сеанс не знайдено.", show_alert=True)
        return

    seats_sold = ""
    config = event.layout_config or {}
    rows = config.get("rows", 0)
    seats_per_row = config.get("seats_per_row", 0)
    total_seats = rows * seats_per_row

    text = (
        f"🎬 <b>{event.title}</b>\n\n"
        f"📅 Дата: {format_datetime(event.datetime)}\n"
        f"💰 Ціна: {format_price(event.base_price)}\n"
        f"🪑 Місць у залі: {total_seats if total_seats else 'не вказано'}\n\n"
        "Натисніть «Вибрати місце» для відкриття схеми залу."
    )
    await callback.message.edit_text(
        text, reply_markup=cinema_event_detail_keyboard(event_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cinema:pay:"))
async def cb_cinema_pay(callback: CallbackQuery, db_user: User) -> None:
    order_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        payment_svc = PaymentService(session)
        ticket_svc = TicketService(session)

        order = await payment_svc.simulate_payment(order_id, db_user.id)
        if not order:
            await callback.answer("❌ Замовлення не знайдено або вже оброблено.", show_alert=True)
            return

        ticket, qr_image_bytes = await ticket_svc.create_ticket(order)
        await session.commit()

    # Надсилаємо QR-код
    from aiogram.types import BufferedInputFile
    qr_file = BufferedInputFile(qr_image_bytes, filename=f"ticket_{ticket.id}.png")
    seat = ""
    if order.seat_details:
        row = order.seat_details.get("row", "")
        seat_num = order.seat_details.get("seat", "")
        seat = f"\n🪑 Ряд {row}, Місце {seat_num}"

    await callback.message.answer_photo(
        photo=qr_file,
        caption=(
            f"✅ <b>Оплата успішна!</b>\n\n"
            f"🎬 <b>{ticket.event.title}</b>\n"
            f"📅 {format_datetime(ticket.event.datetime)}"
            f"{seat}\n"
            f"💰 {format_price(order.total_price)}\n\n"
            f"🎟 Покажіть QR-код контролеру при вході.\n"
            f"ID квитка: #{ticket.id}"
        ),
    )
    await callback.answer("🎟 Квиток готовий!")


@router.callback_query(F.data.startswith("cinema:cancel:"))
async def cb_cinema_cancel(callback: CallbackQuery, db_user: User) -> None:
    order_id = int(callback.data.split(":")[2])
    async with async_session_factory() as session:
        repo = OrderRepository(session)
        await repo.cancel(order_id)
        await session.commit()

    await callback.message.edit_text(
        "❌ Замовлення скасовано.", reply_markup=back_keyboard("category:cinema")
    )
    await callback.answer()


# ── Web App Data (після вибору місця у Mini App) ─────────────

@router.message(F.web_app_data)
async def handle_cinema_webapp_data(message: Message, db_user: User) -> None:
    """Обробляє дані від Mini App після вибору місця."""
    try:
        data = json.loads(message.web_app_data.data)
    except (json.JSONDecodeError, AttributeError):
        await message.answer("❌ Помилка отримання даних.")
        return

    if data.get("category") != "cinema":
        return  # Передаємо далі для обробки bus-хендлером

    event_id = data.get("event_id")
    row = data.get("row")
    seat = data.get("seat")
    seat_key = data.get("seat_key", f"{row}_{seat}")
    price = data.get("price")

    if not all([event_id, row is not None, seat is not None, price]):
        await message.answer("❌ Некоректні дані від Mini App.")
        return

    async with async_session_factory() as session:
        svc = CinemaService(session)
        event = await svc.get_event(event_id)
        if not event:
            await message.answer("❌ Сеанс не знайдено.")
            return

        order, error = await svc.create_order_from_seat(
            user=db_user,
            event_id=event_id,
            seat_key=seat_key,
            row=row,
            seat=seat,
            price=price,
        )
        await session.commit()

    if error:
        await message.answer(f"❌ {error}")
        return

    await message.answer(
        f"🎬 <b>{event.title}</b>\n"
        f"📅 {format_datetime(event.datetime)}\n"
        f"🪑 Ряд {row}, Місце {seat}\n"
        f"💰 {format_price(price)}\n\n"
        "Підтвердіть замовлення та перейдіть до оплати:",
        reply_markup=cinema_order_confirm_keyboard(order.id),
    )
