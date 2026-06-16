import hashlib
import hmac
import json
import secrets
import uuid
from time import time
from urllib.parse import parse_qsl

from core.config import settings


def generate_qr_token() -> str:
    return uuid.uuid4().hex + secrets.token_hex(8)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token(token: str, token_hash: str) -> bool:
    return hash_token(token) == token_hash


def generate_payment_payload(order_id: int) -> str:
    return f"order_{order_id}_{secrets.token_hex(4)}"


def parse_telegram_init_data(init_data: str, max_age_seconds: int = 86400) -> dict | None:
    if not init_data:
        return None

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    auth_date = pairs.get("auth_date")
    if auth_date:
        try:
            if time() - int(auth_date) > max_age_seconds:
                return None
        except ValueError:
            return None

    user_raw = pairs.get("user")
    if user_raw:
        try:
            pairs["user"] = json.loads(user_raw)
        except json.JSONDecodeError:
            return None
    return pairs
