from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any, List


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
    database_auto_create_tables: bool = True

    # Security
    secret_key: str = "change-me-in-production"

    # Payments
    payment_provider_token: str = ""
    payment_currency: str = "UAH"

    # Admin
    admin_ids: List[int] = []

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Any) -> List[int]:
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False
    cors_origins: List[str] = []

    # Seat lock timeout in seconds
    seat_lock_timeout: int = 600

    # Verification timeout in seconds
    verification_timeout: int = 120

    @property
    def full_webhook_url(self) -> str:
        return f"{self.webhook_url}{self.webhook_path}"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if not self.debug and (
            self.secret_key == "change-me-in-production" or len(self.secret_key) < 32
        ):
            raise ValueError("SECRET_KEY must be set to a random 32+ character value in production")
        if not self.debug and self.database_auto_create_tables:
            raise ValueError("DATABASE_AUTO_CREATE_TABLES must be false in production; run Alembic migrations")
        return self


settings = Settings()
