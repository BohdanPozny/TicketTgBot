from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Order, OrderStatus
from database.repositories.orders import OrderRepository
from database.repositories.tickets import TicketRepository


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.ticket_repo = TicketRepository(session)

    async def simulate_payment(self, order_id: int, user_id: int) -> Order | None:
        order = await self.get_payable_order(order_id, user_id)
        if not order:
            return None
        return await self.order_repo.mark_paid(order_id)

    async def process_by_payload(self, payload: str, user_id: int | None = None) -> Order | None:
        order = await self.order_repo.get_by_payment_payload(payload)
        if not order or order.status != OrderStatus.pending:
            return None
        if user_id is not None and order.user_id != user_id:
            return None
        if not await self._can_pay_order(order):
            return None
        return await self.order_repo.mark_paid(order.id)

    async def get_payable_order(self, order_id: int, user_id: int) -> Order | None:
        order = await self.order_repo.get_by_id(order_id)
        if not order or order.user_id != user_id or order.status != OrderStatus.pending:
            return None
        if not await self._can_pay_order(order):
            return None
        return order

    async def can_pay_order(self, order: Order) -> bool:
        return await self._can_pay_order(order)

    async def _can_pay_order(self, order: Order) -> bool:
        if not order.seat_details:
            return True

        seat_key = order.seat_details.get("seat_key")
        if not seat_key:
            return False

        if await self.ticket_repo.is_seat_sold(order.event_id, seat_key):
            return False

        return await self.order_repo.has_active_lock(
            event_id=order.event_id,
            seat_key=seat_key,
            user_id=order.user_id,
        )
