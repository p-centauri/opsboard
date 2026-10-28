from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import SESSION_COOKIE
from app.models import LoginFailure, User, UserSession
from app.security import hash_session_token
from app.services.auth import FAILURE_WINDOW, MAX_FAILURES_PER_EMAIL_IP, MAX_FAILURES_PER_IP
from tests.factories import PASSWORD, make_user


def _login(client: TestClient, email: str, password: str = PASSWORD) -> int:
    response = client.post("/auth/login", json={"email": email, "password": password})
    return int(response.status_code)


def test_login_sets_hardened_session_cookie(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Production default; local .env turns it off for plain-http development.
    monkeypatch.setattr(get_settings(), "cookie_secure", True)
    user = make_user(db, "manager")

    response = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["email"] == user.email
    assert response.json()["role"] == "manager"
    assert "password_hash" not in response.json()
    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    for flag in ("httponly", "secure", "samesite=lax", "path=/", "max-age=43200"):
        assert flag in cookie


def test_session_stores_only_token_hash(client: TestClient, db: Session) -> None:
    user = make_user(db)
    _login(client, user.email)
    token = client.cookies[SESSION_COOKIE]

    stored = db.scalars(select(UserSession.token_hash).where(UserSession.user_id == user.id)).all()

    assert stored == [hash_session_token(token)]


def test_login_email_is_case_insensitive(client: TestClient, db: Session) -> None:
    user = make_user(db)
    assert _login(client, f"  {user.email.upper()} ") == 200


def test_me_returns_signed_in_user(client: TestClient, login: Callable[[str], User]) -> None:
    user = login("viewer")
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["id"] == user.id


def test_wrong_password_and_unknown_email_fail_identically(client: TestClient, db: Session) -> None:
    user = make_user(db)
    wrong_password = client.post("/auth/login", json={"email": user.email, "password": "nope"})
    unknown_email = client.post("/auth/login", json={"email": "ghost@test.local", "password": "x"})

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["error"]["code"] == "invalid_credentials"
    assert SESSION_COOKIE not in client.cookies


def test_inactive_user_cannot_sign_in(client: TestClient, db: Session) -> None:
    user = make_user(db, active=False)
    assert _login(client, user.email) == 401


def test_login_rejects_unknown_fields(client: TestClient, db: Session) -> None:
    user = make_user(db)
    response = client.post(
        "/auth/login", json={"email": user.email, "password": PASSWORD, "role": "admin"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"role": "Extra inputs are not permitted"}


def test_protected_endpoint_requires_session(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_forged_token_is_rejected(client: TestClient) -> None:
    client.cookies.set(SESSION_COOKIE, "forged-token-value")
    assert client.get("/auth/me").status_code == 401


def test_expired_session_is_rejected(
    client: TestClient, db: Session, login: Callable[[str], User]
) -> None:
    user = login("viewer")
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id)
        .values(expires_at=func.now() - FAILURE_WINDOW)
    )
    assert client.get("/auth/me").status_code == 401


def test_logout_revokes_the_session(client: TestClient, login: Callable[[str], User]) -> None:
    login("viewer")
    token = client.cookies[SESSION_COOKIE]

    assert client.post("/auth/logout").status_code == 204

    client.cookies.set(SESSION_COOKIE, token)  # replaying the old cookie must not work
    assert client.get("/auth/me").status_code == 401


def test_logout_without_session_is_harmless(client: TestClient) -> None:
    assert client.post("/auth/logout").status_code == 204


def test_deactivated_user_loses_existing_session(
    client: TestClient, db: Session, login: Callable[[str], User]
) -> None:
    user = login("manager")
    db.execute(update(User).where(User.id == user.id).values(is_active=False))
    assert client.get("/auth/me").status_code == 401


# --- Rate limiting ------------------------------------------------------------------------


def test_repeated_failures_block_even_the_correct_password(client: TestClient, db: Session) -> None:
    user = make_user(db)
    for _ in range(MAX_FAILURES_PER_EMAIL_IP):
        assert _login(client, user.email, "wrong") == 401

    response = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "too_many_attempts"


def test_lockout_is_per_client_ip(client: TestClient, db: Session) -> None:
    """Someone failing on a shared demo account must not lock it for everyone else."""
    user = make_user(db)
    for _ in range(MAX_FAILURES_PER_EMAIL_IP):
        _login(client, user.email, "wrong")

    with TestClient(client.app, base_url="https://testserver", client=("10.9.8.7", 5000)) as other:
        assert _login(other, user.email) == 200


def test_per_ip_cap_stops_spraying_across_emails(client: TestClient, db: Session) -> None:
    victim = make_user(db)
    for n in range(MAX_FAILURES_PER_IP):
        _login(client, f"spray{n}@test.local", "wrong")
    assert _login(client, victim.email) == 429


def test_old_failures_expire(client: TestClient, db: Session) -> None:
    user = make_user(db)
    for _ in range(MAX_FAILURES_PER_EMAIL_IP):
        _login(client, user.email, "wrong")
    db.execute(update(LoginFailure).values(created_at=func.now() - FAILURE_WINDOW))

    assert _login(client, user.email) == 200


def test_failed_login_is_recorded_without_password(client: TestClient, db: Session) -> None:
    user = make_user(db)
    _login(client, user.email, "hunter2")
    rows = db.execute(select(LoginFailure.email, LoginFailure.ip)).all()
    assert [tuple(r) for r in rows] == [(user.email, "testclient")]
