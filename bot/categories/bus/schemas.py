from pydantic import BaseModel
from typing import Any, Optional


class BusSeatSelection(BaseModel):
    """Дані, що надходять від Mini App після вибору місця (автобус)."""
    event_id: int
    seat_number: int
    seat_key: str
    price: float


class BusLayoutConfig(BaseModel):
    """Конфігурація салону автобуса."""
    total_seats: int
    seats_per_row: int = 4  # Зазвичай 2+2
    blocked_seats: list[str] = []
    has_driver_seat: bool = True
    last_row_full: bool = True  # Задній ряд на всю ширину
    category: str = "bus"
