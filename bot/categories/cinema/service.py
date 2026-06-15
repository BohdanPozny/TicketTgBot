from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import generate_payment_payload
from core.utils import format_datetime, format_price
from database.models import Event, User
from database.repositories.events import EventRepository
from database.repositories.orders import OrderRepository


class CinemaService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.event_repo = EventRepository(session)
        self.order_repo = OrderRepository(session)

    async def get_active_sessions(self) -> list[Event]:
        return await self.event_repo.get_active_events_by_category("cinema")

    async def get_event(self, event_id: int) -> Event | None:
        return await self.event_repo.get_event_by_id(event_id)

    async def format_event_list(self, events: list[Event]) -> str:
        if not events:
            return "😔 Наразі немає доступних кіносеансів.\n\nЗаходьте пізніше!"
        lines = ["🎬 <b>Доступні кіносеанси:</b>\n"]
        for event in events:
            lines.append(
                f"▪️ <b>{event.title}</b>\n"
                f"  📅 {format_datetime(event.datetime)}\n"
                f"  💰 {format_price(event.base_price)}\n"
            )
        return "\n".join(lines)

    async def create_order_from_seat(
        self,
        user: User,
        event_id: int,
        seat_key: str,
        row: int,
        seat: int,
        price: float,
    ):
        """Блокує місце та створює замовлення."""
        expires_at = datetime.now() + timedelta(seconds=settings.seat_lock_timeout)

        lock = await self.order_repo.lock_seat(
            event_id=event_id,
            seat_key=seat_key,
            user_id=user.id,
            expires_at=expires_at,
        )
        if not lock:
            return None, "Це місце вже зайнято. Оберіть інше."

        payload = generate_payment_payload(0)  # order_id отримаємо після flush
        order = await self.order_repo.create(
            user_id=user.id,
            event_id=event_id,
            total_price=price,
            seat_details={"row": row, "seat": seat, "seat_key": seat_key},
            payment_payload=payload,
        )
        # Оновлюємо payload з реальним order_id
        order.payment_payload = generate_payment_payload(order.id)
        return order, None
