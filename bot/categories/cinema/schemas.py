from pydantic import BaseModel
from typing import Any, Optional


class CinemaSeatSelection(BaseModel):
    """Дані, що надходять від Mini App після вибору місця (кіно)."""
    event_id: int
    row: int
    seat: int
    seat_key: str
    price: float


class CinemaLayoutConfig(BaseModel):
    """Конфігурація кінозалу."""
    rows: int
    seats_per_row: int
    blocked_seats: list[str] = []  # ["1_3", "1_4"] — ряд_місце
    screen_label: str = "ЕКРАН"
    category: str = "cinema"
