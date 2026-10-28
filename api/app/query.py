"""Shared query helpers: safe LIKE patterns, sorting from an allowlist, pagination."""

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import QueryableAttribute, Session

from app.schemas.common import PageParams

LIKE_ESCAPE = "\\"


def _escape_like(text: str) -> str:
    # User text must never act as a wildcard: "50%" searches for "50%", not "50<anything>".
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def contains(text: str) -> str:
    return f"%{_escape_like(text)}%"


def starts_with(text: str) -> str:
    return f"{_escape_like(text)}%"


def sort_clause(
    sort: str,
    columns: Mapping[str, QueryableAttribute[Any]],
    tiebreaker: QueryableAttribute[Any],
) -> list[ColumnElement[Any]]:
    """`sort` is "<field>" or "-<field>", already validated against `columns` by the schema.
    The tiebreaker keeps pagination stable when sort values repeat."""
    descending = sort.startswith("-")
    column = columns[sort.removeprefix("-")]
    return [
        column.desc() if descending else column.asc(),
        tiebreaker.desc() if descending else tiebreaker.asc(),
    ]


def paginate(
    db: Session, stmt: Select[*tuple[Any, ...]], params: PageParams
) -> tuple[Sequence[Any], int]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(stmt.limit(params.page_size).offset(params.offset)).all()
    return rows, total
