"""Tests run against a real Postgres database (TEST_DATABASE_URL), recreated per session."""

import os
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine
from sqlalchemy.orm import Session

from alembic import command
from app.db import build_engine
from app.deps import get_db
from app.main import app
from app.models import User
from app.seed import truncate_seeded_tables
from tests.factories import PASSWORD, make_user
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


@pytest.fixture
def db(conn: Connection) -> Iterator[Session]:
    """ORM session inside the test's rolled-back transaction. The app's db.commit() only
    releases a savepoint, so each test still starts from an empty database."""
    with Session(bind=conn, join_transaction_mode="create_savepoint") as session:
        yield session


@pytest.fixture
def client(conn: Connection) -> Iterator[TestClient]:
    def request_session() -> Iterator[Session]:
        # Like production: one session per request; closing it without commit rolls back
        # (here: to a savepoint), so a failed request leaves no partial writes behind.
        with Session(bind=conn, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_db] = request_session
    # https, so the Secure session cookie is sent back like a browser would.
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def login(client: TestClient, db: Session) -> Callable[[str], User]:
    """Create a user with the role and sign the client in as them."""

    def _login(role: str) -> User:
        user = make_user(db, role)
        response = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})
        assert response.status_code == 200, response.text
        return user

    return _login
