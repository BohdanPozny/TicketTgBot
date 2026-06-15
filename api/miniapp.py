from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from database.db_setup import get_session
from database.repositories.events import EventRepository
from database.repositories.orders import OrderRepository
from database.repositories.tickets import TicketRepository

router = APIRouter(prefix="/api", tags=["miniapp"])


# ── Pydantic Schemas ──────────────────────────────────────────

class LayoutUpdateRequest(BaseModel):
    layout_config: dict[str, Any]
    partner_telegram_id: int  # Для перевірки прав


class CreateEventRequest(BaseModel):
    partner_telegram_id: int
    category_code: str
    title: str
    event_datetime: str  # ISO format
    base_price: float
    layout_config: Optional[dict[str, Any]] = None


class SeatLockRequest(BaseModel):
    user_telegram_id: int
    seat_key: str


# ── Endpoints ────────────────────────────────────────────────

@router.get("/events/{event_id}/layout")
async def get_event_layout(
    event_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Повертає конфігурацію схеми залу/салону для Mini App."""
    repo = EventRepository(session)
    event = await repo.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Отримати зайняті місця
    ticket_repo = TicketRepository(session)
    order_repo = OrderRepository(session)
    paid_seats = await ticket_repo.get_paid_seats_for_event(event_id)
    locked_seats = await order_repo.get_locked_seats(event_id)

    occupied = list(set(paid_seats + locked_seats))

    return {
        "event_id": event.id,
        "title": event.title,
        "datetime": event.datetime.isoformat(),
        "base_price": event.base_price,
        "layout_config": event.layout_config or {},
        "occupied_seats": occupied,
        "category": event.category.code if event.category else "unknown",
    }


@router.put("/events/{event_id}/layout")
async def update_event_layout(
    event_id: int,
    body: LayoutUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Партнер зберігає схему місць після редагування у Mini App."""
    from database.repositories.users import UserRepository

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(body.partner_telegram_id)
    if not user or user.role.value not in ("partner", "admin"):
        raise HTTPException(status_code=403, detail="Forbidden")

    event_repo = EventRepository(session)
    event = await event_repo.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Перевіряємо право на подію
    partner = await event_repo.get_partner_by_user_id(user.id)
    if not partner or (event.partner_id != partner.id and user.role.value != "admin"):
        raise HTTPException(status_code=403, detail="Not your event")

    updated = await event_repo.update_layout(event_id, body.layout_config)
    return {"ok": True, "event_id": event_id}


@router.post("/events/{event_id}/seats/lock")
async def lock_seat(
    event_id: int,
    body: SeatLockRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Тимчасово блокує місце під час вибору у Mini App."""
    from database.repositories.users import UserRepository

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(body.user_telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    order_repo = OrderRepository(session)
    expires_at = datetime.now() + timedelta(seconds=settings.seat_lock_timeout)
    lock = await order_repo.lock_seat(
        event_id=event_id,
        seat_key=body.seat_key,
        user_id=user.id,
        expires_at=expires_at,
    )
    if not lock:
        raise HTTPException(status_code=409, detail="Seat already locked")

    return {"ok": True, "seat_key": body.seat_key, "expires_at": expires_at.isoformat()}
