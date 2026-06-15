from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Telegram Bot
    bot_token: str
    bot_username: str = "TicketBot"
    webhook_url: str = ""
    webhook_path: str = "/webhook"

    # Database
    database_url: str = "mysql+aiomysql://root:root@localhost:3306/ticketbot"

    # Security
    secret_key: str = "change-me-in-production"

    # Admin
    admin_ids: List[int] = []

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    # Seat lock timeout in seconds
    seat_lock_timeout: int = 600

    # Verification timeout in seconds
    verification_timeout: int = 120

    @property
    def full_webhook_url(self) -> str:
        return f"{self.webhook_url}{self.webhook_path}"


settings = Settings()
