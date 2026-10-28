"""Tests run against a real Postgres database (TEST_DATABASE_URL), recreated per session."""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine

from alembic import command
from app.db import build_engine
from app.seed import truncate_seeded_tables
from tests.helpers import alembic_config, recreate_database


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        raise RuntimeError("TEST_DATABASE_URL is not set. Run tests with `make test`.")
    return url


@pytest.fixture(scope="session")
def database_url() -> str:
    return _test_database_url()


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    recreate_database(database_url)
    eng = build_engine(database_url, 5, 30_000)
    with eng.begin() as conn:
        command.upgrade(alembic_config(conn), "head")
    yield eng
    eng.dispose()


@pytest.fixture
def conn(engine: Engine) -> Iterator[Connection]:
    """A connection whose transaction is rolled back after the test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


@pytest.fixture
def clean_db(engine: Engine) -> Iterator[Engine]:
    """For tests that commit (e.g. the seed): truncate everything afterwards."""
    yield engine
    with engine.begin() as connection:
        truncate_seeded_tables(connection)
