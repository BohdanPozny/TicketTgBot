from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from database.models import Ticket, TicketStatus, TicketVerification, VerificationStatus
from database.repositories.tickets import TicketRepository


class VerificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ticket_repo = TicketRepository(session)

    async def start_verification(self, ticket: Ticket, controller) -> TicketVerification | None:
        existing = await self.ticket_repo.get_pending_verification(ticket.id)
        if existing:
            return None

        await self.ticket_repo.set_status(ticket.id, TicketStatus.verification_pending)
        return await self.ticket_repo.create_verification(ticket.id, controller.id)

    async def process_response(
        self,
        verification_id: int,
        user_id: int,
        confirmed: bool,
    ) -> tuple[TicketVerification, Ticket] | None:
        result = await self.session.execute(
            select(TicketVerification).where(TicketVerification.id == verification_id)
        )
        verification = result.scalar_one_or_none()

        if not verification or verification.status != VerificationStatus.requested:
            return None

        ticket = await self.ticket_repo.get_by_id(verification.ticket_id)
        if not ticket or ticket.user_id != user_id:
            return None

        if confirmed:
            await self.ticket_repo.update_verification_status(verification_id, VerificationStatus.confirmed)
            await self.ticket_repo.set_status(ticket.id, TicketStatus.used)
        else:
            await self.ticket_repo.update_verification_status(verification_id, VerificationStatus.rejected)
            await self.ticket_repo.set_status(ticket.id, TicketStatus.paid)

        return verification, ticket

    async def expire_verification(self, verification_id: int) -> None:
        result = await self.session.execute(
            select(TicketVerification).where(TicketVerification.id == verification_id)
        )
        verification = result.scalar_one_or_none()
        if verification and verification.status == VerificationStatus.requested:
            await self.ticket_repo.update_verification_status(verification_id, VerificationStatus.expired)
            await self.ticket_repo.set_status(verification.ticket_id, TicketStatus.paid)

    async def expire_stale_verifications(self) -> int:
        cutoff = datetime.now() - timedelta(seconds=settings.verification_timeout)
        result = await self.session.execute(
            select(TicketVerification).where(
                TicketVerification.status == VerificationStatus.requested,
                TicketVerification.created_at <= cutoff,
            )
        )
        verifications = list(result.scalars().all())
        for verification in verifications:
            await self.ticket_repo.update_verification_status(
                verification.id,
                VerificationStatus.expired,
            )
            await self.ticket_repo.set_status(verification.ticket_id, TicketStatus.paid)
        return len(verifications)
