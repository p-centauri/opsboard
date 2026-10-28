from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.models import AuditLog


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """{field: [old, new]} for fields that changed."""
    return {
        key: [_jsonable(before.get(key)), _jsonable(value)]
        for key, value in after.items()
        if before.get(key) != value
    }


def record(
    db: Session, user_id: int, entity: str, entity_id: int, action: str, diff: dict[str, Any]
) -> None:
    """Runs in the caller's transaction: the entry exists if and only if the change does."""
    db.execute(
        insert(AuditLog).values(
            user_id=user_id, entity=entity, entity_id=entity_id, action=action, diff=_jsonable(diff)
        )
    )
