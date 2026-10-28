import logging
from datetime import timedelta

from fastapi import APIRouter, Request, Response

from app.config import get_settings
from app.deps import SESSION_COOKIE, CurrentUser, Db
from app.errors import ApiError
from app.schemas.users import LoginIn, UserOut
from app.services import auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    # Behind a proxy, uvicorn --proxy-headers sets this from X-Forwarded-For
    # for trusted proxies only (FORWARDED_ALLOW_IPS).
    return request.client.host if request.client else "unknown"


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Db) -> UserOut:
    ip = _client_ip(request)
    auth.ensure_login_allowed(db, body.email, ip)

    user = auth.authenticate(db, body.email, body.password)
    if user is None:
        auth.record_login_failure(db, body.email, ip)
        db.commit()  # the failure must count even though the request fails
        logger.info("Failed sign-in for %s from %s", body.email, ip)
        raise ApiError(401, "invalid_credentials", "Email or password is incorrect")

    settings = get_settings()
    ttl = timedelta(hours=settings.session_ttl_hours)
    token = auth.create_session(db, user.id, ttl)
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(ttl.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return UserOut.model_validate(user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Db) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        auth.delete_session(db, token)
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
