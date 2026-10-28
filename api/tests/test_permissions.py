"""Who may call what. Every protected endpoint is listed, so a new route without a role check
shows up as a missing row here (see test_every_route_is_covered)."""

from collections.abc import Callable

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app
from app.models import User

PUBLIC = {("GET", "/health"), ("POST", "/auth/login"), ("POST", "/auth/logout")}

# (method, path, minimum role). Bodies are deliberately empty: an allowed role gets past the
# role check and then fails validation (422), a disallowed one is stopped first (403).
ENDPOINTS: list[tuple[str, str, str]] = [
    ("GET", "/auth/me", "viewer"),
    ("GET", "/customers", "viewer"),
    ("GET", "/customers/1", "viewer"),
    ("POST", "/customers", "manager"),
    ("PATCH", "/customers/1", "manager"),
    ("GET", "/products", "viewer"),
    ("GET", "/products/1", "viewer"),
    ("POST", "/products", "manager"),
    ("PATCH", "/products/1", "manager"),
    ("GET", "/orders", "viewer"),
    ("GET", "/orders/export.csv", "viewer"),
    ("GET", "/orders/1", "viewer"),
    ("POST", "/orders", "manager"),
    ("PATCH", "/orders/1", "manager"),
    ("POST", "/orders/1/transition", "manager"),
    ("GET", "/analytics/summary", "viewer"),
    ("GET", "/analytics/revenue-trend", "viewer"),
    ("GET", "/analytics/top-products", "viewer"),
    ("GET", "/analytics/status-breakdown", "viewer"),
    ("GET", "/users", "admin"),
    ("PATCH", "/users/999999", "admin"),
    ("GET", "/audit", "admin"),
]
RANK = {"viewer": 0, "manager": 1, "admin": 2}


def _call(client: TestClient, method: str, path: str) -> int:
    body: dict[str, object] | None = {} if method in ("POST", "PATCH") else None
    return int(client.request(method, path, json=body).status_code)


def _shape(path: str) -> str:
    """ "/orders/{order_id}" and "/orders/1" both become "/orders/{}"."""
    return "/".join(
        "{}" if part.isdigit() or part.startswith("{") else part for part in path.split("/")
    )


def test_every_route_is_covered() -> None:
    routes = {
        (method, _shape(route.path))
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods or set()
    }
    covered = {(m, _shape(p)) for m, p, _ in ENDPOINTS} | PUBLIC
    assert routes - covered == set()


@pytest.mark.parametrize(("method", "path", "_role"), ENDPOINTS)
def test_anonymous_gets_401(client: TestClient, method: str, path: str, _role: str) -> None:
    assert _call(client, method, path) == 401


@pytest.mark.parametrize("role", ["viewer", "manager", "admin"])
@pytest.mark.parametrize(("method", "path", "minimum"), ENDPOINTS)
def test_role_matrix(
    client: TestClient,
    login: Callable[[str], User],
    role: str,
    method: str,
    path: str,
    minimum: str,
) -> None:
    login(role)
    status = _call(client, method, path)
    if RANK[role] >= RANK[minimum]:
        assert status not in (401, 403), f"{role} should be allowed {method} {path}"
    else:
        assert status == 403, f"{role} should be denied {method} {path}"
