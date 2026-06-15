import hashlib
import secrets
import uuid


def generate_qr_token() -> str:
    return uuid.uuid4().hex + secrets.token_hex(8)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token(token: str, token_hash: str) -> bool:
    return hash_token(token) == token_hash


def generate_payment_payload(order_id: int) -> str:
    return f"order_{order_id}_{secrets.token_hex(4)}"
