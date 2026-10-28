from functools import lru_cache

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings from environment variables. Required values have no default,
    so a missing variable fails at startup instead of silently using a dev value."""

    model_config = SettingsConfigDict(extra="ignore")

    database_url: PostgresDsn
    db_connect_timeout_s: int = 5
    db_statement_timeout_ms: int = 10_000

    session_ttl_hours: int = 12
    # Secure by default; only plain-http local dev turns it off (see .env.example).
    cookie_secure: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
