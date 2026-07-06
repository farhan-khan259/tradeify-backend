from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
    )

    PROJECT_NAME: str = "Tradeify"
    API_V1_PREFIX: str = "/api/v1"

    # Supabase Postgres connection string (see backend README for how to get it).
    DATABASE_URL: str = "postgresql+psycopg://tradeify:tradeify@localhost:5432/tradeify"
    # Set true when using Supabase's transaction pooler (port 6543).
    DB_USE_NULL_POOL: bool = False
    # Auto-create tables on startup. Turn off once you manage schema via db/schema.sql.
    AUTO_CREATE_TABLES: bool = True

    # Optional: only needed if you later use the supabase-py client / Storage / Auth.
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ALGORITHM: str = "HS256"

    # Demo: return the password-reset token in the API response (no email service wired up).
    # Set false in production — tokens must only be delivered out-of-band via email.
    EXPOSE_RESET_TOKEN: bool = True
    EXPOSE_FORGOT_PASSWORD_OTP: bool = True
    PASSWORD_RESET_OTP_EXPIRE_MINUTES: int = 10

    SMTP_HOST: str = Field("smtp.gmail.com", env=["SMTP_HOST"])
    SMTP_PORT: int = Field(587, env=["SMTP_PORT"])
    SMTP_USERNAME: str = Field("", env=["SMTP_USERNAME", "EMAIL_USER"])
    SMTP_PASSWORD: str = Field("", env=["SMTP_PASSWORD", "EMAIL_PASS"])
    SMTP_FROM_EMAIL: str = Field("", env=["SMTP_FROM_EMAIL", "EMAIL_USER"])
    SMTP_USE_TLS: bool = Field(True, env=["SMTP_USE_TLS"])

    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    FIRST_ADMIN_EMAIL: str = "admin@tradeify.com"
    FIRST_ADMIN_PASSWORD: str = "ChangeMe123!"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
