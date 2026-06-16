from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, Message, PreCheckoutQuery

from bot.common.keyboards import back_keyboard, main_menu_keyboard, ticket_verification_keyboard
from core.security import hash_token
from core.utils import format_datetime, format_price
from database.db_setup import async_session_factory
from database.models import Ticket, TicketStatus, User
from database.repositories.tickets import TicketRepository
from database.repositories.users import UserRepository
from services.payment_service import PaymentService
from services.ticket_service import TicketService
from services.verification_service import VerificationService

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User) -> None:
    args = message.text.split(maxsplit=1)
    deep_link = args[1] if len(args) > 1 else None

    if deep_link and deep_link.startswith("verify_"):
        await _handle_verification(message, db_user, deep_link[len("verify_"):])
        return

    name = db_user.first_name or db_user.username or "Користувач"
    await message.answer(
        f"👋 Вітаємо, <b>{name}</b>!\n\n"
        "🎟 <b>TicketBot</b> — сервіс для купівлі електронних квитків.\n\n"
        "Оберіть категорію:",
        reply_markup=main_menu_keyboard(db_user.role.value),
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, db_user: User) -> None:
    name = db_user.first_name or db_user.username or "Користувач"
    await callback.message.edit_text(
        f"👋 Вітаємо, <b>{name}</b>!\n\nОберіть категорію:",
        reply_markup=main_menu_keyboard(db_user.role.value),
    )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message, db_user: User) -> None:
    role_text = {
        "customer": "👤 Роль: <b>Клієнт</b>",
        "partner": "🏢 Роль: <b>Партнер</b>",
        "admin": "⚙️ Роль: <b>Адміністратор</b>",
    }.get(db_user.role.value, "👤 Клієнт")

    await message.answer(
        f"{role_text}\n\n"
        "/start — головне меню\n"
        "/help — довідка\n"
        "/tickets — мої квитки\n\n"
        "<b>Як купити квиток:</b>\n"
        "1. Оберіть категорію\n"
        "2. Виберіть подію або рейс\n"
        "3. Оберіть місце у Mini App\n"
        "4. Підтвердіть і оплатіть\n"
        "5. Отримайте QR-квиток",
    )


@router.message(Command("tickets"))
@router.callback_query(F.data == "my_tickets")
async def show_my_tickets(event, db_user: User) -> None:
    is_callback = isinstance(event, CallbackQuery)
    message = event.message if is_callback else event

    async with async_session_factory() as session:
        repo = TicketRepository(session)
        tickets = await repo.get_user_tickets(db_user.id)

    if not tickets:
        text = "У вас ще немає квитків."
    else:
        status_emoji = {
            "paid": "✅", "pending": "⏳", "used": "☑️",
            "cancelled": "❌", "expired": "⌛", "verification_pending": "🔍",
        }
        lines = ["<b>Ваші квитки:</b>\n"]
        for ticket in tickets[:10]:
            emoji = status_emoji.get(ticket.status.value, "🎟")
            seat = ""
            if ticket.seat_details:
                row = ticket.seat_details.get("row", "")
                seat_num = ticket.seat_details.get("seat", "")
                seat = f" | Ряд {row}, Місце {seat_num}" if row else f" | Місце {seat_num}"
            lines.append(
                f"{emoji} <b>{ticket.event.title}</b>\n"
                f"   {format_datetime(ticket.event.datetime)}{seat}\n"
                f"   #{ticket.id}\n"
            )
        text = "\n".join(lines)

    if is_callback:
        await message.edit_text(text, reply_markup=back_keyboard())
        await event.answer()
    else:
        await message.answer(text, reply_markup=back_keyboard())


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    async with async_session_factory() as session:
        payment_svc = PaymentService(session)
        order = await payment_svc.order_repo.get_by_payment_payload(pre_checkout_query.invoice_payload)
        if (
            not order
            or order.user.telegram_id != pre_checkout_query.from_user.id
            or not await payment_svc.can_pay_order(order)
        ):
            await pre_checkout_query.answer(
                ok=False,
                error_message="Замовлення вже недоступне. Оберіть місце ще раз.",
            )
            return

    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, db_user: User) -> None:
    payment = message.successful_payment
    async with async_session_factory() as session:
        payment_svc = PaymentService(session)
        ticket_svc = TicketService(session)

        order = await payment_svc.process_by_payload(payment.invoice_payload, user_id=db_user.id)
        if not order:
            await message.answer("❌ Не вдалося обробити оплату. Зверніться до підтримки.")
            return

        ticket, qr_image_bytes = await ticket_svc.create_ticket(order)
        await session.commit()

    seat = ""
    if ticket.seat_details:
        row = ticket.seat_details.get("row")
        seat_num = ticket.seat_details.get("seat")
        if row:
            seat = f"\n🪑 Ряд {row}, Місце {seat_num}"
        elif seat_num:
            seat = f"\n🪑 Місце {seat_num}"

    qr_file = BufferedInputFile(qr_image_bytes, filename=f"ticket_{ticket.id}.png")
    await message.answer_photo(
        photo=qr_file,
        caption=(
            f"✅ <b>Оплата успішна!</b>\n\n"
            f"<b>{ticket.event.title}</b>\n"
            f"📅 {format_datetime(ticket.event.datetime)}"
            f"{seat}\n"
            f"💰 {format_price(order.total_price)}\n\n"
            "🎟 Покажіть QR-код контролеру.\n"
            f"ID квитка: #{ticket.id}"
        ),
    )


async def _handle_verification(message: Message, controller: User, token: str) -> None:
    token_hash = hash_token(token)

    async with async_session_factory() as session:
        ticket_repo = TicketRepository(session)
        ticket = await ticket_repo.get_by_qr_hash(token_hash)

        if not ticket:
            await message.answer("❌ Квиток не знайдено.")
            return

        if ticket.status == TicketStatus.used:
            await message.answer(f"⚠️ Квиток вже використано ({format_datetime(ticket.used_at)}).")
            return

        if ticket.status == TicketStatus.cancelled:
            await message.answer("❌ Квиток скасовано.")
            return

        if ticket.status not in (TicketStatus.paid, TicketStatus.verification_pending):
            await message.answer("❌ Квиток недійсний.")
            return

        verification_svc = VerificationService(session)
        verification = await verification_svc.start_verification(ticket, controller)
        await session.commit()

    if not verification:
        await message.answer("⚠️ Для цього квитка вже є активний запит на верифікацію.")
        return

    seat_info = ""
    if ticket.seat_details:
        row = ticket.seat_details.get("row", "")
        seat_num = ticket.seat_details.get("seat", "")
        seat_info = f"\nМісце: Ряд {row}, Місце {seat_num}" if row else f"\nМісце: {seat_num}"

    await message.answer(
        f"🔍 <b>Квиток знайдено</b>\n\n"
        f"<b>{ticket.event.title}</b>\n"
        f"{format_datetime(ticket.event.datetime)}"
        f"{seat_info}\n\n"
        "Очікуємо підтвердження від власника..."
    )

    from bot.loader import bot
    try:
        await bot.send_message(
            chat_id=ticket.user.telegram_id,
            text=(
                f"🔔 <b>Ваш квиток відскановано</b>\n\n"
                f"<b>{ticket.event.title}</b>\n"
                f"{format_datetime(ticket.event.datetime)}"
                f"{seat_info}\n\n"
                "Підтверджуєте прохід?"
            ),
            reply_markup=ticket_verification_keyboard(verification.id),
        )
    except Exception:
        await message.answer("⚠️ Не вдалося надіслати запит власнику квитка.")


@router.callback_query(F.data.startswith("verify:confirm:"))
async def cb_verify_confirm(callback: CallbackQuery, db_user: User) -> None:
    verification_id = int(callback.data.split(":")[2])
    await _process_verification(callback, db_user, verification_id, confirmed=True)


@router.callback_query(F.data.startswith("verify:reject:"))
async def cb_verify_reject(callback: CallbackQuery, db_user: User) -> None:
    verification_id = int(callback.data.split(":")[2])
    await _process_verification(callback, db_user, verification_id, confirmed=False)


async def _process_verification(
    callback: CallbackQuery, db_user: User, verification_id: int, confirmed: bool
) -> None:
    from bot.loader import bot

    async with async_session_factory() as session:
        svc = VerificationService(session)
        result = await svc.process_response(verification_id, db_user.id, confirmed)
        await session.commit()

    if result is None:
        await callback.answer("Запит не знайдено або вже оброблено.", show_alert=True)
        return

    verification, ticket = result

    if confirmed:
        await callback.message.edit_text("✅ Прохід підтверджено. Дякуємо!")
        controller_tg_id = await _get_controller_tg_id(verification.controller_id)
        if controller_tg_id:
            try:
                await bot.send_message(controller_tg_id, "✅ Власник підтвердив прохід. Квиток використано.")
            except Exception:
                pass
    else:
        await callback.message.edit_text("❌ Прохід відхилено.")
        controller_tg_id = await _get_controller_tg_id(verification.controller_id)
        if controller_tg_id:
            try:
                await bot.send_message(controller_tg_id, "❌ Власник відхилив прохід.")
            except Exception:
                pass

    await callback.answer()


async def _get_controller_tg_id(controller_id: int) -> int | None:
    async with async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(controller_id)
        return user.telegram_id if user else None
