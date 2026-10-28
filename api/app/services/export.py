"""Streamed CSV export of filtered orders: constant memory however many rows match."""

import csv
import io
from collections.abc import Iterator

from sqlalchemy import Select
from sqlalchemy.orm import Session

from app.models import Customer, Order

EXPORT_MAX_ROWS = 100_000
FETCH_BATCH = 1_000
HEADER = ("number", "created_at", "status", "customer_id", "customer", "total")
# Spreadsheet apps execute cells starting with these as formulas (CSV injection).
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: str) -> str:
    return f"'{value}" if value.startswith(FORMULA_PREFIXES) else value


def stream_orders_csv(db: Session, orders: Select[Order, Customer]) -> Iterator[str]:
    """Yields the CSV in chunks of FETCH_BATCH rows, read through a server-side cursor."""
    stmt = orders.with_only_columns(
        Order.number, Order.created_at, Order.status, Customer.id, Customer.name, Order.total
    ).execution_options(yield_per=FETCH_BATCH)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADER)
    for partition in db.execute(stmt).partitions():
        for number, created_at, status, customer_id, customer_name, total in partition:
            writer.writerow(
                (
                    number,
                    created_at.isoformat(),
                    status,
                    customer_id,
                    safe_cell(customer_name),
                    total,
                )
            )
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
    if buffer.tell():  # header only: no rows matched
        yield buffer.getvalue()
