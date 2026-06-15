import io
import segno
from core.config import settings
from core.utils import build_deep_link


class QRService:
    @staticmethod
    def generate_qr_image(token: str) -> bytes:
        deep_link = build_deep_link(settings.bot_username, token)
        qr = segno.make(deep_link, error="M")
        buffer = io.BytesIO()
        qr.save(buffer, kind="png", scale=10, border=2, dark="#1a1a2e", light="#ffffff")
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def get_deep_link(token: str) -> str:
        return build_deep_link(settings.bot_username, token)
