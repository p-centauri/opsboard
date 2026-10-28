"""User management, audit log, and the error shape."""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.main import app
from app.models import User, UserSession
from tests.factories import PASSWORD, make_customer, make_user


@pytest.fixture
def admin(login: Callable[[str], User]) -> User:
    return login("admin")


def _session_count(db: Session, user_id: int) -> int:
    return db.scalar(select(func.count()).where(UserSession.user_id == user_id)) or 0


def test_admin_lists_users(client: TestClient, db: Session, admin: User) -> None:
    make_user(db, "viewer")
    body = client.get("/users?sort=-created_at").json()
    assert body["total"] == 2
    assert all("password_hash" not in u for u in body["items"])


def test_changing_role_ends_that_users_sessions(
    client: TestClient, db: Session, admin: User
) -> None:
    target = make_user(db, "viewer")
    with TestClient(app, base_url="https://testserver") as other:
        other.post("/auth/login", json={"email": target.email, "password": PASSWORD})
    assert _session_count(db, target.id) == 1

    response = client.patch(f"/users/{target.id}", json={"role": "manager"})

    assert response.status_code == 200
    assert response.json()["role"] == "manager"
    assert _session_count(db, target.id) == 0


def test_deactivated_user_cannot_sign_in(client: TestClient, db: Session, admin: User) -> None:
    target = make_user(db, "manager")
    assert client.patch(f"/users/{target.id}", json={"is_active": False}).status_code == 200

    with TestClient(app, base_url="https://testserver") as other:
        response = other.post("/auth/login", json={"email": target.email, "password": PASSWORD})
    assert response.status_code == 401


def test_admin_cannot_modify_self(client: TestClient, admin: User) -> None:
    response = client.patch(f"/users/{admin.id}", json={"role": "viewer"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "cannot_modify_self"


def test_invalid_role_is_422(client: TestClient, db: Session, admin: User) -> None:
    target = make_user(db)
    assert client.patch(f"/users/{target.id}", json={"role": "root"}).status_code == 422


def test_audit_log_lists_and_filters(client: TestClient, db: Session, admin: User) -> None:
    customer = make_customer(db, name="Before")
    client.patch(f"/customers/{customer.id}", json={"name": "After"})
    target = make_user(db)
    client.patch(f"/users/{target.id}", json={"role": "manager"})

    everything = client.get("/audit").json()
    customers_only = client.get(f"/audit?entity=customer&entity_id={customer.id}").json()

    assert everything["total"] == 2
    assert everything["items"][0]["entity"] == "user"  # newest first
    assert customers_only["total"] == 1
    entry = customers_only["items"][0]
    assert (entry["user_email"], entry["action"]) == (admin.email, "update")
    assert entry["diff"] == {"name": ["Before", "After"]}


# --- Error shape --------------------------------------------------------------------------


def test_unknown_route_uses_error_shape(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found"}}


def test_wrong_method_uses_error_shape(client: TestClient) -> None:
    response = client.delete("/health")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_malformed_json_is_422(client: TestClient) -> None:
    response = client.post(
        "/auth/login", content=b"{not json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.fixture
def broken_dependency() -> Iterator[None]:
    def explode() -> User:
        raise RuntimeError("database password is hunter2")

    app.dependency_overrides[get_current_user] = explode
    yield
    del app.dependency_overrides[get_current_user]


def test_unhandled_error_is_500_without_leaking_details(
    client: TestClient, broken_dependency: None
) -> None:
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as raw:
        response = raw.get("/auth/me")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Something went wrong"}
    }
    assert "hunter2" not in response.text
