"""The database itself rejects invalid data, whatever code path writes it."""

from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import Connection, delete, insert, select
from sqlalchemy.exc import IntegrityError

from app.models import Customer, Order, OrderItem, Product, User


@pytest.fixture
def customer_id(conn: Connection) -> int:
    return conn.execute(
        insert(Customer)
        .values(name="Acme", email="a@acme.example", country="US")
        .returning(Customer.id)
    ).scalar_one()


@pytest.fixture
def product_id(conn: Connection) -> int:
    return conn.execute(
        insert(Product)
        .values(sku="SKU-1", name="Widget", price=Decimal("9.99"), stock_qty=5)
        .returning(Product.id)
    ).scalar_one()


@pytest.fixture
def order_id(conn: Connection, customer_id: int) -> int:
    return conn.execute(
        insert(Order)
        .values(customer_id=customer_id, status="draft", total=Decimal("0"))
        .returning(Order.id)
    ).scalar_one()


def _user(**overrides: Any) -> dict[str, Any]:
    return {"email": "x@demo.local", "password_hash": "h", "role": "viewer"} | overrides


@pytest.mark.parametrize(
    ("values", "constraint"),
    [
        (_user(email="Upper@demo.local"), "ck_users_email_lowercase"),
        (_user(role="superuser"), "ck_users_role_valid"),
    ],
)
def test_user_rejects_invalid_values(
    conn: Connection, values: dict[str, Any], constraint: str
) -> None:
    with pytest.raises(IntegrityError, match=constraint):
        conn.execute(insert(User).values(**values))


def test_user_email_is_unique(conn: Connection) -> None:
    conn.execute(insert(User).values(**_user()))
    with pytest.raises(IntegrityError, match="uq_users_email"):
        conn.execute(insert(User).values(**_user(role="admin")))


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"price": Decimal("-0.01")}, "ck_products_price_non_negative"),
        ({"stock_qty": -1}, "ck_products_stock_non_negative"),
        ({"low_stock_threshold": -1}, "ck_products_threshold_non_negative"),
    ],
)
def test_product_rejects_negative_values(
    conn: Connection, overrides: dict[str, Any], constraint: str
) -> None:
    values = {"sku": "SKU-X", "name": "X", "price": Decimal("1"), "stock_qty": 1} | overrides
    with pytest.raises(IntegrityError, match=constraint):
        conn.execute(insert(Product).values(**values))


def test_product_sku_is_unique(conn: Connection, product_id: int) -> None:
    with pytest.raises(IntegrityError, match="uq_products_sku"):
        conn.execute(
            insert(Product).values(sku="SKU-1", name="Dup", price=Decimal("1"), stock_qty=1)
        )


def test_customer_country_must_be_iso2(conn: Connection) -> None:
    with pytest.raises(IntegrityError, match="ck_customers_country_iso2"):
        conn.execute(insert(Customer).values(name="A", email="a@a.example", country="U"))


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"status": "lost"}, "ck_orders_status_valid"),
        ({"total": Decimal("-1")}, "ck_orders_total_non_negative"),
        ({"version": 0}, "ck_orders_version_positive"),
        ({"customer_id": 999_999}, "fk_orders_customer_id_customers"),
    ],
)
def test_order_rejects_invalid_values(
    conn: Connection, customer_id: int, overrides: dict[str, Any], constraint: str
) -> None:
    values = {"customer_id": customer_id, "status": "draft", "total": Decimal("0")} | overrides
    with pytest.raises(IntegrityError, match=constraint):
        conn.execute(insert(Order).values(**values))


def test_order_number_is_derived_from_id(conn: Connection, order_id: int) -> None:
    number = conn.execute(select(Order.number).where(Order.id == order_id)).scalar_one()
    assert number == f"ORD-{order_id:07d}"


def test_order_defaults(conn: Connection, order_id: int) -> None:
    order = conn.execute(select(Order).where(Order.id == order_id)).one()
    assert order.version == 1
    assert order.created_at is not None and order.updated_at is not None


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"qty": 0}, "ck_order_items_qty_positive"),
        ({"unit_price": Decimal("-1")}, "ck_order_items_unit_price_non_negative"),
    ],
)
def test_order_item_rejects_invalid_values(
    conn: Connection, order_id: int, product_id: int, overrides: dict[str, Any], constraint: str
) -> None:
    values = {"order_id": order_id, "product_id": product_id, "qty": 1, "unit_price": Decimal("1")}
    with pytest.raises(IntegrityError, match=constraint):
        conn.execute(insert(OrderItem).values(**(values | overrides)))


def test_order_item_product_once_per_order(
    conn: Connection, order_id: int, product_id: int
) -> None:
    item = {"order_id": order_id, "product_id": product_id, "qty": 1, "unit_price": Decimal("1")}
    conn.execute(insert(OrderItem).values(**item))
    with pytest.raises(IntegrityError, match="uq_order_items_order_id"):
        conn.execute(insert(OrderItem).values(**item))


def test_deleting_order_deletes_its_items(conn: Connection, order_id: int, product_id: int) -> None:
    conn.execute(
        insert(OrderItem).values(
            order_id=order_id, product_id=product_id, qty=1, unit_price=Decimal("1")
        )
    )
    conn.execute(delete(Order).where(Order.id == order_id))
    assert conn.execute(select(OrderItem).where(OrderItem.order_id == order_id)).first() is None
