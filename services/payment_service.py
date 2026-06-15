from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Order, OrderStatus
from database.repositories.orders import OrderRepository


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)

    async def simulate_payment(self, order_id: int, user_id: int) -> Order | None:
        order = await self.order_repo.get_by_id(order_id)
        if not order or order.user_id != user_id or order.status != OrderStatus.pending:
            return None
        return await self.order_repo.mark_paid(order_id)

    async def process_by_payload(self, payload: str) -> Order | None:
        order = await self.order_repo.get_by_payment_payload(payload)
        if not order or order.status != OrderStatus.pending:
            return None
        return await self.order_repo.mark_paid(order.id)
