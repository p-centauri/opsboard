"""Small helpers shared by the simple create/update endpoints (customers, products)."""

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ApiError, violated_constraint

# Unique constraints that clients can hit, mapped to the field they should fix.
UNIQUE_FIELDS = {"uq_products_sku": ("sku", "A product with this SKU already exists")}


def flush_or_conflict(db: Session) -> None:
    """Flush pending writes; turn a known unique-constraint violation into a 409 on its field."""
    try:
        db.flush()
    except IntegrityError as exc:
        known = UNIQUE_FIELDS.get(violated_constraint(exc) or "")
        if known is None:
            raise
        field, message = known
        raise ApiError(409, "conflict", message, {field: message}) from exc


def apply_changes(obj: Any, changes: dict[str, Any]) -> dict[str, Any]:
    """Set attributes; return {field: [old, new]} for the ones that actually changed."""
    diff: dict[str, Any] = {}
    for field, new in changes.items():
        old = getattr(obj, field)
        if old != new:
            diff[field] = [old, new]
            setattr(obj, field, new)
    return diff
