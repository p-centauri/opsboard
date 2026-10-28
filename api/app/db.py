from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app.config import get_settings


def build_engine(database_url: str, connect_timeout_s: int, statement_timeout_ms: int) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": connect_timeout_s,
            "options": f"-c statement_timeout={statement_timeout_ms}",
        },
    )


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return build_engine(
        str(settings.database_url),
        settings.db_connect_timeout_s,
        settings.db_statement_timeout_ms,
    )
