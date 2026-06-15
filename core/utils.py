from datetime import datetime
from typing import Any


def format_datetime(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y %H:%M")


def format_price(price: float) -> str:
    return f"{price:.2f} грн"


def build_deep_link(bot_username: str, token: str) -> str:
    return f"https://t.me/{bot_username}?start=verify_{token}"


def seat_key_from_details(seat_details: dict[str, Any]) -> str:
    row = seat_details.get("row", "")
    seat = seat_details.get("seat", "")
    return f"{row}_{seat}"


def chunk_list(lst: list, size: int) -> list[list]:
    return [lst[i : i + size] for i in range(0, len(lst), size)]
