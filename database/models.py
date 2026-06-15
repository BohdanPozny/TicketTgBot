from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger, DateTime, Enum, Float, ForeignKey,
    Integer, JSON, String, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    customer = "customer"
    partner = "partner"
    admin = "admin"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    cancelled = "cancelled"
    expired = "expired"


class TicketStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    verification_pending = "verification_pending"
    used = "used"
    cancelled = "cancelled"
    expired = "expired"


class VerificationStatus(str, enum.Enum):
    requested = "requested"
    confirmed = "confirmed"
    rejected = "rejected"
    expired = "expired"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.customer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    partner_profile: Mapped[Optional["Partner"]] = relationship(back_populates="user", uselist=False, lazy="select")
    orders: Mapped[list["Order"]] = relationship(back_populates="user", lazy="select")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="user", lazy="select")
    seat_locks: Mapped[list["SeatLock"]] = relationship(back_populates="user", lazy="select")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    emoji: Mapped[str] = mapped_column(String(10), default="🎟", nullable=False)

    events: Mapped[list["Event"]] = relationship(back_populates="category", lazy="select")


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="partner_profile")
    events: Mapped[list["Event"]] = relationship(back_populates="partner", lazy="select")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_id: Mapped[int] = mapped_column(Integer, ForeignKey("partners.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    layout_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    partner: Mapped["Partner"] = relationship(back_populates="events")
    category: Mapped["Category"] = relationship(back_populates="events")
    orders: Mapped[list["Order"]] = relationship(back_populates="event", lazy="select")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="event", lazy="select")
    seat_locks: Mapped[list["SeatLock"]] = relationship(back_populates="event", lazy="select")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.pending, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    payment_payload: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seat_details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="orders")
    event: Mapped["Event"] = relationship(back_populates="orders")
    ticket: Mapped[Optional["Ticket"]] = relationship(back_populates="order", uselist=False, lazy="select")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    seat_details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), default=TicketStatus.paid, nullable=False)
    qr_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="ticket")
    user: Mapped["User"] = relationship(back_populates="tickets")
    event: Mapped["Event"] = relationship(back_populates="tickets")
    verifications: Mapped[list["TicketVerification"]] = relationship(back_populates="ticket", lazy="select")


class SeatLock(Base):
    __tablename__ = "seat_locks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    seat_key: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    event: Mapped["Event"] = relationship(back_populates="seat_locks")
    user: Mapped["User"] = relationship(back_populates="seat_locks")


class TicketVerification(Base):
    __tablename__ = "ticket_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    controller_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus), default=VerificationStatus.requested, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    ticket: Mapped["Ticket"] = relationship(back_populates="verifications")
