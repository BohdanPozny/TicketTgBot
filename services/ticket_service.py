from sqlalchemy.ext.asyncio import AsyncSession

from core.security import generate_qr_token, hash_token
from database.models import Order, Ticket
from database.repositories.tickets import TicketRepository
from services.qr_service import QRService


class TicketService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ticket_repo = TicketRepository(session)

    async def create_ticket(self, order: Order) -> tuple[Ticket, bytes]:
        token = generate_qr_token()
        token_hash = hash_token(token)

        ticket = await self.ticket_repo.create(
            order_id=order.id,
            user_id=order.user_id,
            event_id=order.event_id,
            qr_token_hash=token_hash,
            seat_details=order.seat_details,
        )

        await self.session.refresh(ticket, ["event"])
        if ticket.event:
            await self.session.refresh(ticket.event, ["category"])

        qr_bytes = QRService.generate_qr_image(token)
        return ticket, qr_bytes
