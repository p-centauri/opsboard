import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from argon2 import PasswordHasher
from faker import Faker
from sqlalchemy import Engine, func, insert, select, text

from app import seed
from app.models import Customer, Order, OrderItem, OrderStatus, Product, User
from app.seed import (
    ItemRow,
    OrderRow,
    SeedConfig,
    SeedPasswords,
    generate_orders,
    generate_products,
    seed_database,
)

END = datetime(2026, 1, 1, tzinfo=UTC)
SMALL = SeedConfig(customers=20, products=15, orders=300, seed=7, end=END)
PASSWORDS = SeedPasswords(demo="demo-pw", admin="admin-pw")


def _orders(cfg: SeedConfig) -> list[tuple[OrderRow, list[ItemRow]]]:
    rng = random.Random(cfg.seed)
    return list(generate_orders(rng, cfg, generate_products(rng, cfg)))


def _fingerprint(engine: Engine) -> str:
    """Hash of every seeded business row, to compare two seed runs."""
    with engine.connect() as conn:
        digest: str = conn.execute(
            text(
                "SELECT md5(string_agg(t, '|' ORDER BY t)) FROM ("
                " SELECT row(c.*)::text t FROM customers c"
                " UNION ALL SELECT row(p.*)::text FROM products p"
                " UNION ALL SELECT row(o.*)::text FROM orders o"
                " UNION ALL SELECT row(i.*)::text FROM order_items i) rows"
            )
        ).scalar_one()
    return digest


# --- Pure generators ----------------------------------------------------------------------


def test_same_seed_generates_identical_data() -> None:
    assert _orders(SMALL) == _orders(SMALL)


def test_different_seed_generates_different_data() -> None:
    assert _orders(SMALL) != _orders(SeedConfig(20, 15, 300, seed=8, end=END))


def test_orders_are_chronological_and_within_history_window() -> None:
    stamps = [order.created_at for order, _ in _orders(SMALL)]
    assert stamps == sorted(stamps)
    assert min(stamps) >= END - timedelta(days=seed.HISTORY_DAYS)
    assert max(stamps) < END


def test_order_total_equals_sum_of_items_and_items_are_valid() -> None:
    for order, items in _orders(SMALL):
        assert items, "every order has at least one item"
        assert order.total == sum((i.qty * i.unit_price for i in items), Decimal("0"))
        product_ids = [i.product_id for i in items]
        assert len(product_ids) == len(set(product_ids)), "a product appears once per order"
        assert all(i.qty > 0 for i in items)


def test_status_depends_on_order_age() -> None:
    rng = random.Random(1)
    old = {seed._status_for_age(rng, timedelta(days=30)) for _ in range(500)}
    recent = {seed._status_for_age(rng, timedelta(hours=5)) for _ in range(500)}
    assert old == {OrderStatus.DELIVERED, OrderStatus.CANCELLED}
    assert OrderStatus.DRAFT in recent and OrderStatus.DELIVERED not in recent


def test_customer_emails_use_reserved_example_domain() -> None:
    faker = Faker()
    faker.seed_instance(1)
    rows = seed.generate_customers(random.Random(1), faker, SMALL)
    assert len(rows) == SMALL.customers
    assert all(row.email.endswith(".example") for row in rows)


def test_product_names_are_unique() -> None:
    products = generate_products(random.Random(5), SeedConfig(10, 1_000, 1, seed=5, end=END))
    assert len({p.name for p in products}) == 1_000


def test_too_many_products_for_unique_names_fails_loudly() -> None:
    with pytest.raises(ValueError, match="unique names"):
        generate_products(random.Random(5), SeedConfig(10, 100_000, 1, seed=5, end=END))


def test_products_include_low_stock_items() -> None:
    products = generate_products(random.Random(3), SeedConfig(10, 500, 1, seed=3, end=END))
    assert any(p.stock_qty <= p.low_stock_threshold for p in products)
    assert all(p.price > 0 for p in products)


# --- Database seeding ---------------------------------------------------------------------


def test_seed_loads_consistent_data(clean_db: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(seed, "BATCH_SIZE", 100)  # exercise several COPY batches

    seed_database(clean_db, SMALL, PASSWORDS, reset=False)

    with clean_db.connect() as conn:
        assert conn.execute(select(func.count()).select_from(Customer)).scalar_one() == 20
        assert conn.execute(select(func.count()).select_from(Product)).scalar_one() == 15
        assert conn.execute(select(func.count()).select_from(Order)).scalar_one() == 300
        mismatched = conn.execute(
            text(
                "SELECT count(*) FROM orders o WHERE o.total <>"
                " (SELECT sum(qty * unit_price) FROM order_items i WHERE i.order_id = o.id)"
            )
        ).scalar_one()
        assert mismatched == 0
        assert conn.execute(select(func.max(Order.number))).scalar_one() == "ORD-0000300"


def test_seed_creates_one_user_per_role_with_hashed_passwords(clean_db: Engine) -> None:
    seed_database(clean_db, SMALL, PASSWORDS, reset=False)

    with clean_db.connect() as conn:
        users = {u.email: u for u in conn.execute(select(User)).all()}
    assert {u.role for u in users.values()} == {"viewer", "manager", "admin"}
    hasher = PasswordHasher()
    assert hasher.verify(users["manager@demo.local"].password_hash, "demo-pw")
    assert hasher.verify(users["admin@demo.local"].password_hash, "admin-pw")
    assert "demo-pw" not in users["viewer@demo.local"].password_hash


def test_seed_syncs_identity_so_new_rows_get_next_ids(clean_db: Engine) -> None:
    seed_database(clean_db, SMALL, PASSWORDS, reset=False)

    with clean_db.begin() as conn:
        new_id = conn.execute(
            insert(Order)
            .values(customer_id=1, status="draft", total=Decimal("0"))
            .returning(Order.id)
        ).scalar_one()
        item_id = conn.execute(
            insert(OrderItem)
            .values(order_id=new_id, product_id=1, qty=1, unit_price=Decimal("1"))
            .returning(OrderItem.id)
        ).scalar_one()
        max_seeded_item = conn.execute(
            select(func.max(OrderItem.id)).where(OrderItem.order_id != new_id)
        ).scalar_one()
    assert new_id == 301
    assert item_id == max_seeded_item + 1


def test_seed_refuses_to_overwrite_existing_data(clean_db: Engine) -> None:
    seed_database(clean_db, SMALL, PASSWORDS, reset=False)
    before = _fingerprint(clean_db)

    with pytest.raises(SystemExit, match="already has data"):
        seed_database(clean_db, SMALL, PASSWORDS, reset=False)

    assert _fingerprint(clean_db) == before


def test_reseed_with_same_seed_is_deterministic(clean_db: Engine) -> None:
    seed_database(clean_db, SMALL, PASSWORDS, reset=False)
    first = _fingerprint(clean_db)

    seed_database(clean_db, SMALL, PASSWORDS, reset=True)

    assert _fingerprint(clean_db) == first


def test_seed_is_all_or_nothing(clean_db: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(seed, "_sync_identity", fail)

    with pytest.raises(RuntimeError, match="boom"):
        seed_database(clean_db, SMALL, PASSWORDS, reset=False)

    with clean_db.connect() as conn:
        assert conn.execute(select(func.count()).select_from(Order)).scalar_one() == 0
        assert conn.execute(select(func.count()).select_from(User)).scalar_one() == 0


# --- CLI ----------------------------------------------------------------------------------


def test_cli_requires_password_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEED_DEMO_PASSWORD", raising=False)
    with pytest.raises(SystemExit, match="SEED_DEMO_PASSWORD is required"):
        seed.main(["--orders", "1"])


@pytest.mark.parametrize("arg", ["--orders", "--customers", "--products"])
def test_cli_rejects_non_positive_counts(arg: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        seed.main([arg, "0"])
    assert "must be at least 1" in capsys.readouterr().err


def test_cli_rejects_bad_end_date(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        seed.main(["--end-date", "2026-13-01"])
    assert "invalid iso_date value: '2026-13-01'" in capsys.readouterr().err
