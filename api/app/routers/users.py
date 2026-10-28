from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlalchemy import select

from app import audit
from app.deps import Admin, Db
from app.errors import ApiError, not_found
from app.models import Role, User
from app.query import paginate, sort_clause
from app.schemas.common import Page, PageParams
from app.schemas.users import UserOut, UserUpdate
from app.services import auth

router = APIRouter(prefix="/users", tags=["users"])

SORTABLE = {"email": User.email, "created_at": User.created_at}


class UserListParams(PageParams):
    sort: Literal["email", "-email", "created_at", "-created_at"] = "email"


@router.get("")
def list_users(params: Annotated[UserListParams, Query()], db: Db, _: Admin) -> Page[UserOut]:
    stmt = select(User).order_by(*sort_clause(params.sort, SORTABLE, User.id))
    rows, total = paginate(db, stmt, params)
    return Page(
        items=[UserOut.model_validate(row.User) for row in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.patch("/{user_id}")
def update_user(user_id: int, body: UserUpdate, db: Db, admin: Admin) -> UserOut:
    if user_id == admin.id:
        # Prevents an admin from locking everyone (including themselves) out of admin.
        raise ApiError(409, "cannot_modify_self", "You can't change your own role or status")
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise not_found("User")

    before = {"role": user.role, "is_active": user.is_active}
    if body.role is not None:
        user.role = Role(body.role).value
    if body.is_active is not None:
        user.is_active = body.is_active
    diff = audit.changes(before, {"role": user.role, "is_active": user.is_active})
    if diff:
        # Role or status changed: end existing sessions so the change applies immediately.
        auth.delete_user_sessions(db, user.id)
        audit.record(db, admin.id, "user", user.id, "update", diff)
    db.commit()
    return UserOut.model_validate(user)
