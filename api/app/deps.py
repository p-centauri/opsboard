"""Request-scoped dependencies: DB session, current user, role checks."""

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db import get_engine
from app.errors import ApiError
from app.models import Role, User
from app.services import auth

SESSION_COOKIE = "opsboard_session"
ROLE_RANK = {Role.VIEWER: 0, Role.MANAGER: 1, Role.ADMIN: 2}


def get_db(engine: Annotated[Engine, Depends(get_engine)]) -> Iterator[Session]:
    """One session per request. Writers call db.commit(); anything else is rolled back."""
    with Session(engine) as session:
        yield session


Db = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: Db) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    user = auth.user_for_session(db, token) if token else None
    if user is None:
        raise ApiError(401, "not_authenticated", "Sign in to continue")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(minimum: Role) -> Callable[[User], User]:
    def dependency(user: CurrentUser) -> User:
        if ROLE_RANK[Role(user.role)] < ROLE_RANK[minimum]:
            raise ApiError(403, "forbidden", f"This action requires the {minimum.value} role")
        return user

    return dependency


Viewer = Annotated[User, Depends(require_role(Role.VIEWER))]
Manager = Annotated[User, Depends(require_role(Role.MANAGER))]
Admin = Annotated[User, Depends(require_role(Role.ADMIN))]
