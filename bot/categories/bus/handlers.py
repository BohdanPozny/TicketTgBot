import json

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.categories.bus.keyboards import (
    bus_event_detail_keyboard,
    bus_order_confirm_keyboard,
    bus_routes_keyboard,
)
from bot.categories.bus.service import BusService
from bot.common.keyboards import back_keyboard
from core.utils import format_datetime, format_price
from database.db_setup import async_session_factory
from database.models import User
from database.repositories.orders import OrderRepository
from services.payment_service import PaymentService
from services.ticket_service import TicketService

router = Router(name="bus")


@router.callback_query(F.data == "category:bus")
async def cb_bus_list(callback: CallbackQuery, db_user: User) -> None:
    async with async_session_factory() as session:
        svc = BusService(session)
        events = await svc.get_active_routes()
        text = await svc.format_route_list(events)

    if events:
        await callback.message.edit_text(text, reply_markup=bus_routes_keyboard(events))
    else:
        await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("bus:event:"))
async def cb_bus_event(callback: CallbackQuery, db_user: User) -> None:
    event_id = int(callback.data.split(":")[2])
    async with async_session_factory() as session:
        svc = BusService(session)
        event = await svc.get_event(event_id)

    if not event:
        await callback.answer("❌ Рейс не знайдено.", show_alert=True)
        return

    config = event.layout_config or {}
    dep = config.get("departure_city", "")
    arr = config.get("arrival_city", "")
    carrier = config.get("carrier", "")
    total_seats = config.get("total_seats", 0)

    route_line = f"🗺 Маршрут: {dep} → {arr}\n" if dep and arr else ""
    carrier_line = f"🚌 Перевізник: {carrier}\n" if carrier else ""

    text = (
        f"🚌 <b>{event.title}</b>\n\n"
        f"{route_line}"
        f"📅 Відправлення: {format_datetime(event.datetime)}\n"
        f"{carrier_line}"
        f"💰 Ціна: {format_price(event.base_price)}\n"
        f"🪑 Місць у автобусі: {total_seats if total_seats else 'не вказано'}\n\n"
        "Натисніть «Вибрати місце» для відкриття схеми салону."
    )
    await callback.message.edit_text(text, reply_markup=bus_event_detail_keyboard(event_id))
    await callback.answer()


@router.callback_query(F.data.startswith("bus:pay:"))
async def cb_bus_pay(callback: CallbackQuery, db_user: User) -> None:
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

    from aiogram.types import BufferedInputFile
    qr_file = BufferedInputFile(qr_image_bytes, filename=f"ticket_{ticket.id}.png")
    seat = ""
    if order.seat_details:
        seat_num = order.seat_details.get("seat", "")
        seat = f"\n🪑 Місце {seat_num}"

    config = ticket.event.layout_config or {}
    dep = config.get("departure_city", "")
    arr = config.get("arrival_city", "")
    route = f"\n🗺 {dep} → {arr}" if dep and arr else ""

    await callback.message.answer_photo(
        photo=qr_file,
        caption=(
            f"✅ <b>Оплата успішна!</b>\n\n"
            f"🚌 <b>{ticket.event.title}</b>"
            f"{route}\n"
            f"📅 {format_datetime(ticket.event.datetime)}"
            f"{seat}\n"
            f"💰 {format_price(order.total_price)}\n\n"
            f"🎟 Покажіть QR-код під час посадки.\n"
            f"ID квитка: #{ticket.id}"
        ),
    )
    await callback.answer("🎟 Квиток готовий!")


@router.callback_query(F.data.startswith("bus:cancel:"))
async def cb_bus_cancel(callback: CallbackQuery, db_user: User) -> None:
    order_id = int(callback.data.split(":")[2])
    async with async_session_factory() as session:
        repo = OrderRepository(session)
        await repo.cancel(order_id)
        await session.commit()

    await callback.message.edit_text(
        "❌ Замовлення скасовано.", reply_markup=back_keyboard("category:bus")
    )
    await callback.answer()


@router.message(F.web_app_data)
async def handle_bus_webapp_data(message: Message, db_user: User) -> None:
    try:
        data = json.loads(message.web_app_data.data)
    except (json.JSONDecodeError, AttributeError):
        await message.answer("❌ Помилка отримання даних.")
        return

    if data.get("category") != "bus":
        return

    event_id = data.get("event_id")
    seat_number = data.get("seat_number")
    seat_key = data.get("seat_key", f"seat_{seat_number}")
    price = data.get("price")

    if not all([event_id, seat_number is not None, price]):
        await message.answer("❌ Некоректні дані від Mini App.")
        return

    async with async_session_factory() as session:
        svc = BusService(session)
        event = await svc.get_event(event_id)
        if not event:
            await message.answer("❌ Рейс не знайдено.")
            return

        order, error = await svc.create_order_from_seat(
            user=db_user,
            event_id=event_id,
            seat_key=seat_key,
            seat_number=seat_number,
            price=price,
        )
        await session.commit()

    if error:
        await message.answer(f"❌ {error}")
        return

    config = event.layout_config or {}
    dep = config.get("departure_city", "")
    arr = config.get("arrival_city", "")
    route = f"\n🗺 {dep} → {arr}" if dep and arr else ""

    await message.answer(
        f"🚌 <b>{event.title}</b>"
        f"{route}\n"
        f"📅 {format_datetime(event.datetime)}\n"
        f"🪑 Місце {seat_number}\n"
        f"💰 {format_price(price)}\n\n"
        "Підтвердіть замовлення та перейдіть до оплати:",
        reply_markup=bus_order_confirm_keyboard(order.id),
    )
