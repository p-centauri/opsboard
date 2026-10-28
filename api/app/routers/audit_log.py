from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.deps import Admin, Db
from app.models import AuditLog, User
from app.query import paginate
from app.schemas.common import OutputModel, Page, PageParams

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditParams(PageParams):
    entity: Literal["order", "customer", "product", "user"] | None = None
    entity_id: int | None = None


class AuditEntryOut(OutputModel):
    id: int
    user_id: int | None
    user_email: str | None
    entity: str
    entity_id: int
    action: str
    diff: dict[str, Any]
    created_at: datetime


@router.get("")
def list_audit(params: Annotated[AuditParams, Query()], db: Db, _: Admin) -> Page[AuditEntryOut]:
    stmt = (
        select(AuditLog, User.email)
        .outerjoin(User, User.id == AuditLog.user_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    if params.entity is not None:
        stmt = stmt.where(AuditLog.entity == params.entity)
    if params.entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == params.entity_id)
    rows, total = paginate(db, stmt, params)
    items = [
        AuditEntryOut(
            id=entry.id,
            user_id=entry.user_id,
            user_email=email,
            entity=entry.entity,
            entity_id=entry.entity_id,
            action=entry.action,
            diff=entry.diff,
            created_at=entry.created_at,
        )
        for entry, email in rows
    ]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)
