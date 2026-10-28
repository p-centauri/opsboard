from pathlib import Path

from alembic.config import Config
from sqlalchemy import Connection, make_url, text

from app.db import build_engine

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def recreate_database(url: str) -> None:
    """Drop and create the database named in `url`, connecting via the `postgres` db."""
    parsed = make_url(url)
    admin = build_engine(
        parsed.set(database="postgres").render_as_string(hide_password=False), 5, 30_000
    )
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{parsed.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{parsed.database}"'))
    admin.dispose()


def alembic_config(conn: Connection) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_INI.parent / "alembic"))
    cfg.attributes["connection"] = conn
    return cfg
