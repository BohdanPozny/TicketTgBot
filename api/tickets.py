from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_token
from database.db_setup import get_session
from database.models import TicketStatus
from database.repositories.tickets import TicketRepository
from core.utils import format_datetime

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.get("/{token}")
async def get_ticket_by_token(
    token: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Перевірка квитка за токеном (для зовнішніх систем / контролерів)."""
    token_hash = hash_token(token)
    repo = TicketRepository(session)
    ticket = await repo.get_by_qr_hash(token_hash)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    is_valid = ticket.status in (TicketStatus.paid, TicketStatus.verification_pending)

    seat_info = None
    if ticket.seat_details:
        seat_info = ticket.seat_details

    return {
        "ticket_id": ticket.id,
        "status": ticket.status.value,
        "is_valid": is_valid,
        "event": {
            "id": ticket.event_id,
            "title": ticket.event.title if ticket.event else None,
            "datetime": ticket.event.datetime.isoformat() if ticket.event else None,
        },
        "seat_details": seat_info,
        "created_at": ticket.created_at.isoformat(),
        "used_at": ticket.used_at.isoformat() if ticket.used_at else None,
    }
