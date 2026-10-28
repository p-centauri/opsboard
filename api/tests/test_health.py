from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.db import build_engine, get_engine
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_ok_when_database_reachable(client: TestClient, engine: Engine) -> None:
    app.dependency_overrides[get_engine] = lambda: engine

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_503_when_database_unreachable(client: TestClient) -> None:
    # Port 1 on localhost refuses connections immediately.
    dead = build_engine("postgresql+psycopg://nobody:nothing@127.0.0.1:1/none", 1, 1_000)
    app.dependency_overrides[get_engine] = lambda: dead

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "db_unavailable", "message": "Database unavailable"}
    }
