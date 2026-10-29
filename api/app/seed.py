"""Deterministic demo data: customers, products, ~2 years of orders, and one user per role.

Same --seed and --end-date always produce the same data. Rows are generated in Python and
bulk-loaded with COPY in batches, so 100k orders take seconds and memory stays bounded.

Usage: python -m app.seed [--orders N] [--seed N] [--end-date YYYY-MM-DD] [--reset]
"""

import argparse
import logging
import os
import random
import re
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, NamedTuple

import psycopg
from faker import Faker
from psycopg import sql
from sqlalchemy import Connection, Engine, exists, func, insert, select

from app.db import get_engine
from app.models import Base, OrderStatus, Role, User
from app.security import hash_password

logger = logging.getLogger(__name__)

HISTORY_DAYS = 730
BATCH_SIZE = 10_000
SEEDED_TABLES = (
    "order_items",
    "orders",
    "products",
    "customers",
    "audit_log",
    "user_sessions",
    "login_failures",
    "users",
)

COUNTRIES = ("US", "GB", "DE", "CA", "AU", "NL", "FR", "AE", "UZ", "KZ")
COUNTRY_WEIGHTS = (30, 14, 12, 9, 7, 6, 6, 6, 5, 5)
PRODUCT_ADJECTIVES = (
    "Steel",
    "Compact",
    "Heavy-Duty",
    "Wireless",
    "Ergonomic",
    "Industrial",
    "Portable",
    "Smart",
    "Modular",
    "Premium",
    "Eco",
    "Reinforced",
)
PRODUCT_NOUNS = (
    "Shelf Bracket",
    "Barcode Scanner",
    "Label Printer",
    "Pallet Jack",
    "Storage Bin",
    "Packing Tape",
    "Safety Gloves",
    "Work Bench",
    "Tool Cabinet",
    "Hand Truck",
    "LED Panel",
    "Cable Reel",
    "Office Chair",
    "Desk Lamp",
    "Shipping Box",
    "Air Compressor",
)

PRODUCT_MODELS = ("100", "200", "300", "Mini", "Lite", "Plus", "Pro", "Max")


@dataclass(frozen=True)
class SeedConfig:
    customers: int
    products: int
    orders: int
    seed: int
    end: datetime  # orders are created in [end - HISTORY_DAYS, end)


@dataclass(frozen=True)
class SeedPasswords:
    demo: str  # viewer + manager; public on the live demo
    admin: str


# Row types: field names match table columns, so they double as the COPY column lists.
class CustomerRow(NamedTuple):
    id: int
    name: str
    email: str
    country: str
    created_at: datetime


class ProductRow(NamedTuple):
    id: int
    sku: str
    name: str
    price: Decimal
    stock_qty: int
    low_stock_threshold: int


class OrderRow(NamedTuple):
    id: int
    customer_id: int
    status: str
    total: Decimal
    created_at: datetime
    updated_at: datetime


class ItemRow(NamedTuple):
    id: int
    order_id: int
    product_id: int
    qty: int
    unit_price: Decimal


# --- Pure generators (no I/O) -------------------------------------------------------------


def generate_customers(rng: random.Random, faker: Faker, cfg: SeedConfig) -> list[CustomerRow]:
    history_start = cfg.end - timedelta(days=HISTORY_DAYS)
    rows: list[CustomerRow] = []
    for customer_id in range(1, cfg.customers + 1):
        name = faker.company()
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        # .example is reserved (RFC 2606), so seeded emails never hit a real domain.
        email = f"orders+{customer_id}@{slug}.example"
        country = rng.choices(COUNTRIES, weights=COUNTRY_WEIGHTS)[0]
        created_at = history_start - timedelta(
            days=rng.randint(0, 365), seconds=rng.randint(0, 86_399)
        )
        rows.append(CustomerRow(customer_id, name, email, country, created_at))
    return rows


def generate_products(rng: random.Random, cfg: SeedConfig) -> list[ProductRow]:
    """Products with unique names (duplicate names next to different SKUs look like a data bug)."""
    combinations = len(PRODUCT_ADJECTIVES) * len(PRODUCT_NOUNS) * len(PRODUCT_MODELS)
    if cfg.products > combinations:
        raise ValueError(f"At most {combinations} products have unique names; got {cfg.products}")
    rows: list[ProductRow] = []
    used: set[str] = set()
    for product_id in range(1, cfg.products + 1):
        name = ""
        while not name or name in used:
            name = (
                f"{rng.choice(PRODUCT_ADJECTIVES)} {rng.choice(PRODUCT_NOUNS)} "
                f"{rng.choice(PRODUCT_MODELS)}"
            )
        used.add(name)
        whole_price = round(min(max(rng.lognormvariate(3.6, 1.0), 2), 2_000))
        price = Decimal(whole_price) - Decimal("0.01")  # 1.99 .. 1999.99
        threshold = rng.choice((5, 10, 20, 25))
        # ~8% of products start at or below their threshold so the low-stock view has content.
        stock = (
            rng.randint(0, threshold) if rng.random() < 0.08 else rng.randint(threshold + 1, 600)
        )
        rows.append(ProductRow(product_id, f"SKU-{product_id:05d}", name, price, stock, threshold))
    return rows


def _order_timestamps(rng: random.Random, cfg: SeedConfig) -> list[datetime]:
    """Order times with business growth over the period and a Nov/Dec peak, oldest first."""
    start = cfg.end - timedelta(days=HISTORY_DAYS)
    days = [start + timedelta(days=offset) for offset in range(HISTORY_DAYS)]
    season = {11: 1.5, 12: 1.7, 1: 0.8, 2: 0.85}
    weights = [
        (1 + offset / HISTORY_DAYS) * season.get(day.month, 1.0) for offset, day in enumerate(days)
    ]
    picked = rng.choices(days, weights=weights, k=cfg.orders)
    # The last day starts at end - 1 day, so every stamp is < end.
    return sorted(day + timedelta(seconds=rng.randint(0, 86_399)) for day in picked)


def _status_for_age(rng: random.Random, age: timedelta) -> OrderStatus:
    S = OrderStatus
    options: tuple[OrderStatus, ...]
    weights: tuple[int, ...]
    if age > timedelta(days=14):
        options, weights = (S.DELIVERED, S.CANCELLED), (92, 8)
    elif age > timedelta(days=3):
        options, weights = (S.DELIVERED, S.SHIPPED, S.CONFIRMED, S.CANCELLED), (50, 35, 10, 5)
    else:
        options, weights = (S.DRAFT, S.CONFIRMED, S.SHIPPED, S.CANCELLED), (20, 45, 30, 5)
    return rng.choices(options, weights=weights)[0]


def generate_orders(
    rng: random.Random, cfg: SeedConfig, products: Sequence[ProductRow]
) -> Iterator[tuple[OrderRow, list[ItemRow]]]:
    """Yield (order_row, item_rows) per order. Totals always equal the sum of the items."""
    # A few customers and products account for most volume, as in real sales data.
    customer_ids = range(1, cfg.customers + 1)
    customer_weights = [1 / rank**0.8 for rank in customer_ids]
    product_weights = [1 / rank**0.6 for rank in range(1, len(products) + 1)]
    item_id = 0
    for order_id, created_at in enumerate(_order_timestamps(rng, cfg), start=1):
        picks = rng.choices(products, weights=product_weights, k=rng.choice((1, 1, 2, 2, 3, 4, 5)))
        unique_products = list({product.id: product for product in picks}.values())
        items: list[ItemRow] = []
        total = Decimal("0.00")
        for product in unique_products:
            item_id += 1
            qty = rng.choices((1, 2, 3, 5, 10), weights=(55, 20, 12, 8, 5))[0]
            items.append(ItemRow(item_id, order_id, product.id, qty, product.price))
            total += product.price * qty
        status = _status_for_age(rng, cfg.end - created_at)
        updated_at = min(created_at + timedelta(hours=rng.randint(0, 96)), cfg.end)
        customer_id = rng.choices(customer_ids, weights=customer_weights)[0]
        yield OrderRow(order_id, customer_id, status.value, total, created_at, updated_at), items


# --- Database writes ----------------------------------------------------------------------


def _driver_cursor(conn: Connection) -> psycopg.Cursor[Any]:
    raw = conn.connection.driver_connection
    if not isinstance(raw, psycopg.Connection):
        raise TypeError(f"Seeding needs a psycopg connection, got {type(raw).__name__}")
    return raw.cursor()


def _copy(
    conn: Connection, table: str, columns: Sequence[str], rows: Sequence[tuple[Any, ...]]
) -> None:
    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns))
    )
    with _driver_cursor(conn) as cur, cur.copy(statement) as copy:
        for row in rows:
            copy.write_row(row)


def _sync_identity(conn: Connection, table: str) -> None:
    # COPY with explicit ids doesn't advance the identity sequence; do it so later inserts work.
    id_column = Base.metadata.tables[table].c.id
    conn.execute(select(func.setval(func.pg_get_serial_sequence(table, "id"), func.max(id_column))))


def truncate_seeded_tables(conn: Connection) -> None:
    statement = sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
        sql.SQL(", ").join(map(sql.Identifier, SEEDED_TABLES))
    )
    with _driver_cursor(conn) as cur:
        cur.execute(statement)


def _prepare_tables(conn: Connection, reset: bool) -> None:
    if reset:
        truncate_seeded_tables(conn)
        return
    for table in SEEDED_TABLES:
        if conn.execute(select(exists().select_from(Base.metadata.tables[table]))).scalar_one():
            raise SystemExit(
                f"Table '{table}' already has data. Re-run with --reset to replace it."
            )


def _insert_users(conn: Connection, passwords: SeedPasswords) -> None:
    users = [
        ("viewer@demo.local", Role.VIEWER, passwords.demo),
        ("manager@demo.local", Role.MANAGER, passwords.demo),
        ("admin@demo.local", Role.ADMIN, passwords.admin),
    ]
    conn.execute(
        insert(User),
        [
            {"email": email, "role": role.value, "password_hash": hash_password(pw)}
            for email, role, pw in users
        ],
    )


def seed_database(
    engine: Engine, cfg: SeedConfig, passwords: SeedPasswords, *, reset: bool
) -> None:
    """Load all demo data in one transaction: either everything is seeded or nothing is."""
    rng = random.Random(cfg.seed)
    faker = Faker()
    faker.seed_instance(cfg.seed)
    products = generate_products(rng, cfg)

    with engine.begin() as conn:
        _prepare_tables(conn, reset)
        _insert_users(conn, passwords)
        _copy(conn, "customers", CustomerRow._fields, generate_customers(rng, faker, cfg))
        _copy(conn, "products", ProductRow._fields, products)

        order_batch: list[OrderRow] = []
        item_batch: list[ItemRow] = []

        def flush() -> None:
            _copy(conn, "orders", OrderRow._fields, order_batch)
            _copy(conn, "order_items", ItemRow._fields, item_batch)
            order_batch.clear()
            item_batch.clear()

        for order_row, item_rows in generate_orders(rng, cfg, products):
            order_batch.append(order_row)
            item_batch.extend(item_rows)
            if len(order_batch) >= BATCH_SIZE:
                flush()
        if order_batch:
            flush()

        for table in ("customers", "products", "orders", "order_items"):
            _sync_identity(conn, table)


# --- CLI ----------------------------------------------------------------------------------


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"Environment variable {name} is required (see .env.example).")
    return value


def iso_date(value: str) -> date:
    # Named for argparse's message: "invalid iso_date value: '2026-13-01'".
    return date.fromisoformat(value)


def _end_datetime(end_date: date | None) -> datetime:
    if end_date is None:
        return datetime.now(UTC).replace(second=0, microsecond=0)
    return datetime.combine(end_date, datetime.min.time(), tzinfo=UTC)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Seed the OpsBoard database with demo data.")
    parser.add_argument("--customers", type=int, default=1_000)
    parser.add_argument("--products", type=int, default=300)
    parser.add_argument("--orders", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--end-date", type=iso_date, help="YYYY-MM-DD; orders end at this date (default: now)"
    )
    parser.add_argument("--reset", action="store_true", help="truncate seeded tables first")
    args = parser.parse_args(argv)
    for name in ("customers", "products", "orders"):
        if getattr(args, name) < 1:
            parser.error(f"--{name} must be at least 1")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = SeedConfig(
        args.customers, args.products, args.orders, args.seed, _end_datetime(args.end_date)
    )
    passwords = SeedPasswords(
        _required_env("SEED_DEMO_PASSWORD"), _required_env("SEED_ADMIN_PASSWORD")
    )

    started = time.perf_counter()
    seed_database(get_engine(), cfg, passwords, reset=args.reset)
    logger.info(
        "Seeded %d customers, %d products, %d orders in %.1fs",
        cfg.customers,
        cfg.products,
        cfg.orders,
        time.perf_counter() - started,
    )


if __name__ == "__main__":
    main()
