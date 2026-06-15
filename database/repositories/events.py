from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Category, Event, Partner


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_categories(self) -> list[Category]:
        result = await self.session.execute(select(Category))
        return list(result.scalars().all())

    async def get_category_by_code(self, code: str) -> Optional[Category]:
        result = await self.session.execute(select(Category).where(Category.code == code))
        return result.scalar_one_or_none()

    async def create_category(self, name: str, code: str, emoji: str = "🎟") -> Category:
        cat = Category(name=name, code=code, emoji=emoji)
        self.session.add(cat)
        await self.session.flush()
        return cat

    async def get_partner_by_user_id(self, user_id: int) -> Optional[Partner]:
        result = await self.session.execute(select(Partner).where(Partner.user_id == user_id))
        return result.scalar_one_or_none()

    async def create_partner(self, user_id: int, company_name: Optional[str] = None) -> Partner:
        partner = Partner(user_id=user_id, company_name=company_name)
        self.session.add(partner)
        await self.session.flush()
        return partner

    async def get_or_create_partner(self, user_id: int, company_name: Optional[str] = None) -> tuple[Partner, bool]:
        partner = await self.get_partner_by_user_id(user_id)
        if partner:
            return partner, False
        partner = await self.create_partner(user_id, company_name)
        return partner, True

    async def get_event_by_id(self, event_id: int) -> Optional[Event]:
        result = await self.session.execute(
            select(Event)
            .where(Event.id == event_id)
            .options(selectinload(Event.category), selectinload(Event.partner))
        )
        return result.scalar_one_or_none()

    async def get_active_events_by_category(self, category_code: str) -> list[Event]:
        result = await self.session.execute(
            select(Event)
            .join(Category, Event.category_id == Category.id)
            .where(Category.code == category_code, Event.is_active == True)
            .where(Event.datetime >= datetime.now())
            .options(selectinload(Event.category))
            .order_by(Event.datetime.asc())
        )
        return list(result.scalars().all())

    async def get_events_by_partner(self, partner_id: int) -> list[Event]:
        result = await self.session.execute(
            select(Event)
            .where(Event.partner_id == partner_id)
            .options(selectinload(Event.category))
            .order_by(Event.datetime.desc())
        )
        return list(result.scalars().all())

    async def create_event(
        self,
        partner_id: int,
        category_id: int,
        title: str,
        event_datetime: datetime,
        base_price: float,
        layout_config: Optional[dict[str, Any]] = None,
    ) -> Event:
        event = Event(
            partner_id=partner_id,
            category_id=category_id,
            title=title,
            datetime=event_datetime,
            base_price=base_price,
            layout_config=layout_config,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def update_layout(self, event_id: int, layout_config: dict[str, Any]) -> Optional[Event]:
        event = await self.get_event_by_id(event_id)
        if event:
            event.layout_config = layout_config
        return event
