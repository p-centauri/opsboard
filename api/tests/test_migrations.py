from collections.abc import Iterator

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect, make_url

from alembic import command
from app.db import build_engine
from app.models import Base
from tests.helpers import alembic_config, recreate_database


@pytest.fixture
def scratch_engine(database_url: str) -> Iterator[Engine]:
    """A separate empty database so up/down cycles don't touch the shared test schema."""
    url = make_url(database_url)
    scratch_url = url.set(database=f"{url.database}_migrations").render_as_string(
        hide_password=False
    )
    recreate_database(scratch_url)
    eng = build_engine(scratch_url, 5, 30_000)
    yield eng
    eng.dispose()


def test_migrations_match_models(engine: Engine) -> None:
    """Fails if a model changed without a migration (or vice versa)."""
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_migrations_downgrade_and_upgrade_cleanly(scratch_engine: Engine) -> None:
    with scratch_engine.begin() as conn:
        command.upgrade(alembic_config(conn), "head")
    assert set(Base.metadata.tables) <= set(inspect(scratch_engine).get_table_names())

    with scratch_engine.begin() as conn:
        command.downgrade(alembic_config(conn), "base")
    assert inspect(scratch_engine).get_table_names() == ["alembic_version"]

    with scratch_engine.begin() as conn:
        command.upgrade(alembic_config(conn), "head")
    assert set(Base.metadata.tables) <= set(inspect(scratch_engine).get_table_names())
