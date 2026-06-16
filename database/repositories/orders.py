from datetime import datetime
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Order, OrderStatus, SeatLock


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, order_id: int) -> Optional[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.event), selectinload(Order.user))
        )
        return result.scalar_one_or_none()

    async def get_by_payment_payload(self, payload: str) -> Optional[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.payment_payload == payload)
            .options(selectinload(Order.event), selectinload(Order.user))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: int,
        event_id: int,
        total_price: float,
        seat_details: Optional[dict[str, Any]] = None,
        payment_payload: Optional[str] = None,
    ) -> Order:
        order = Order(
            user_id=user_id,
            event_id=event_id,
            total_price=total_price,
            seat_details=seat_details,
            payment_payload=payment_payload,
            status=OrderStatus.pending,
        )
        self.session.add(order)
        await self.session.flush()
        return order

    async def mark_paid(self, order_id: int) -> Optional[Order]:
        order = await self.get_by_id(order_id)
        if order:
            order.status = OrderStatus.paid
            order.paid_at = datetime.now()
        return order

    async def cancel(self, order_id: int, user_id: Optional[int] = None) -> Optional[Order]:
        order = await self.get_by_id(order_id)
        if not order:
            return None
        if user_id is not None and order.user_id != user_id:
            return None
        if order.status != OrderStatus.pending:
            return None

        order.status = OrderStatus.cancelled
        if order.seat_details and order.seat_details.get("seat_key"):
            await self.release_seat_lock(
                event_id=order.event_id,
                seat_key=order.seat_details["seat_key"],
                user_id=order.user_id,
            )
        return order

    async def get_user_orders(self, user_id: int) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .options(selectinload(Order.event))
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Seat Locks ────────────────────────────────────────────────

    async def lock_seat(
        self, event_id: int, seat_key: str, user_id: int, expires_at: datetime
    ) -> Optional[SeatLock]:
        await self.session.execute(
            delete(SeatLock).where(
                SeatLock.event_id == event_id,
                SeatLock.seat_key == seat_key,
                SeatLock.expires_at <= datetime.now(),
            )
        )

        existing = await self.session.execute(
            select(SeatLock).where(
                SeatLock.event_id == event_id,
                SeatLock.seat_key == seat_key,
                SeatLock.expires_at > datetime.now(),
            )
        )
        if existing.scalar_one_or_none():
            return None

        lock = SeatLock(
            event_id=event_id,
            seat_key=seat_key,
            user_id=user_id,
            expires_at=expires_at,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(lock)
                await self.session.flush()
        except IntegrityError:
            return None
        return lock

    async def has_active_lock(self, event_id: int, seat_key: str, user_id: int) -> bool:
        result = await self.session.execute(
            select(SeatLock).where(
                SeatLock.event_id == event_id,
                SeatLock.seat_key == seat_key,
                SeatLock.user_id == user_id,
                SeatLock.expires_at > datetime.now(),
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_locked_seats(self, event_id: int) -> list[str]:
        """Повертає список ключів заблокованих місць для події."""
        result = await self.session.execute(
            select(SeatLock.seat_key).where(
                SeatLock.event_id == event_id,
                SeatLock.expires_at > datetime.now(),
            )
        )
        return list(result.scalars().all())

    async def release_seat_lock(self, event_id: int, seat_key: str, user_id: int) -> None:
        result = await self.session.execute(
            select(SeatLock).where(
                SeatLock.event_id == event_id,
                SeatLock.seat_key == seat_key,
                SeatLock.user_id == user_id,
            )
        )
        lock = result.scalar_one_or_none()
        if lock:
            await self.session.delete(lock)
