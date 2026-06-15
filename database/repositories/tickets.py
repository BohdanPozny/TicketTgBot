from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Ticket, TicketStatus, TicketVerification, VerificationStatus


class TicketRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(
                selectinload(Ticket.event).selectinload("category"),
                selectinload(Ticket.user),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_qr_hash(self, qr_token_hash: str) -> Optional[Ticket]:
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.qr_token_hash == qr_token_hash)
            .options(
                selectinload(Ticket.event).selectinload("category"),
                selectinload(Ticket.user),
            )
        )
        return result.scalar_one_or_none()

    async def get_paid_seats_for_event(self, event_id: int) -> list[str]:
        """Повертає seat_key оплачених місць для події."""
        result = await self.session.execute(
            select(Ticket).where(
                Ticket.event_id == event_id,
                Ticket.status.in_([TicketStatus.paid, TicketStatus.verification_pending, TicketStatus.used]),
            )
        )
        tickets = result.scalars().all()
        seats = []
        for t in tickets:
            if t.seat_details:
                row = t.seat_details.get("row", "")
                seat = t.seat_details.get("seat", "")
                seats.append(f"{row}_{seat}")
        return seats

    async def create(
        self,
        order_id: int,
        user_id: int,
        event_id: int,
        qr_token_hash: str,
        seat_details: Optional[dict] = None,
    ) -> Ticket:
        ticket = Ticket(
            order_id=order_id,
            user_id=user_id,
            event_id=event_id,
            qr_token_hash=qr_token_hash,
            seat_details=seat_details,
            status=TicketStatus.paid,
        )
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def set_status(self, ticket_id: int, status: TicketStatus) -> Optional[Ticket]:
        ticket = await self.get_by_id(ticket_id)
        if ticket:
            ticket.status = status
            if status == TicketStatus.used:
                ticket.used_at = datetime.now()
        return ticket

    async def get_user_tickets(self, user_id: int) -> list[Ticket]:
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .options(selectinload(Ticket.event))
            .order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Verifications ────────────────────────────────────────────

    async def create_verification(
        self, ticket_id: int, controller_id: int
    ) -> TicketVerification:
        verification = TicketVerification(
            ticket_id=ticket_id,
            controller_id=controller_id,
            status=VerificationStatus.requested,
        )
        self.session.add(verification)
        await self.session.flush()
        return verification

    async def get_pending_verification(self, ticket_id: int) -> Optional[TicketVerification]:
        result = await self.session.execute(
            select(TicketVerification).where(
                TicketVerification.ticket_id == ticket_id,
                TicketVerification.status == VerificationStatus.requested,
            )
        )
        return result.scalar_one_or_none()

    async def update_verification_status(
        self, verification_id: int, status: VerificationStatus
    ) -> Optional[TicketVerification]:
        result = await self.session.execute(
            select(TicketVerification).where(TicketVerification.id == verification_id)
        )
        verification = result.scalar_one_or_none()
        if verification:
            verification.status = status
            if status in (VerificationStatus.confirmed, VerificationStatus.rejected):
                verification.confirmed_at = datetime.now()
        return verification

    async def get_event_stats(self, event_id: int) -> dict:
        """Повертає статистику продажів для події."""
        result = await self.session.execute(
            select(Ticket).where(
                Ticket.event_id == event_id,
                Ticket.status.in_([
                    TicketStatus.paid,
                    TicketStatus.verification_pending,
                    TicketStatus.used,
                ]),
            )
        )
        tickets = list(result.scalars().all())
        return {
            "total_sold": len(tickets),
            "used": sum(1 for t in tickets if t.status == TicketStatus.used),
            "pending_verification": sum(
                1 for t in tickets if t.status == TicketStatus.verification_pending
            ),
        }
