"""Login, server-side sessions, and login rate limiting (all state in Postgres, so it holds
across API replicas)."""

from datetime import timedelta

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import LoginFailure, User, UserSession
from app.security import (
    burn_password_check,
    hash_session_token,
    new_session_token,
    verify_password,
)

FAILURE_WINDOW = timedelta(minutes=15)
# Keyed by email+IP so one client can't lock a shared (demo) account for everyone else.
MAX_FAILURES_PER_EMAIL_IP = 5
# Caps password spraying across many emails from one IP.
MAX_FAILURES_PER_IP = 30


def _recent_failures(db: Session, email: str, ip: str) -> tuple[int, int]:
    since = func.now() - FAILURE_WINDOW
    recent = (LoginFailure.ip == ip) & (LoginFailure.created_at > since)
    per_email_ip, per_ip = db.execute(
        select(
            func.count().filter(LoginFailure.email == email),
            func.count(),
        ).where(recent)
    ).one()
    return per_email_ip, per_ip


def ensure_login_allowed(db: Session, email: str, ip: str) -> None:
    """Soft limit: concurrent attempts can overshoot by a few, which is acceptable here."""
    per_email_ip, per_ip = _recent_failures(db, email, ip)
    if per_email_ip >= MAX_FAILURES_PER_EMAIL_IP or per_ip >= MAX_FAILURES_PER_IP:
        raise ApiError(429, "too_many_attempts", "Too many failed sign-ins. Try again later.")


def record_login_failure(db: Session, email: str, ip: str) -> None:
    db.execute(delete(LoginFailure).where(LoginFailure.created_at < func.now() - FAILURE_WINDOW))
    db.execute(insert(LoginFailure).values(email=email, ip=ip))


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        burn_password_check(password)
        return None
    if not verify_password(user.password_hash, password) or not user.is_active:
        return None
    return user


def create_session(db: Session, user_id: int, ttl: timedelta) -> str:
    """Returns the raw token for the cookie; only its hash is stored."""
    token = new_session_token()
    db.execute(delete(UserSession).where(UserSession.expires_at < func.now()))
    db.execute(
        insert(UserSession).values(
            token_hash=hash_session_token(token), user_id=user_id, expires_at=func.now() + ttl
        )
    )
    return token


def user_for_session(db: Session, token: str) -> User | None:
    return db.scalar(
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(
            UserSession.token_hash == hash_session_token(token),
            UserSession.expires_at > func.now(),
            User.is_active,
        )
    )


def delete_session(db: Session, token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.token_hash == hash_session_token(token)))


def delete_user_sessions(db: Session, user_id: int) -> None:
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))
