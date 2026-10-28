"""Test data builders. They add rows to the given session and flush (no commit)."""

import itertools
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Customer, Order, OrderItem, Product, User
from app.security import hash_password

PASSWORD = "correct-horse-battery"
_PASSWORD_HASH = hash_password(PASSWORD)  # hashed once: argon2 is deliberately slow
_seq = itertools.count(1)


def make_user(db: Session, role: str = "viewer", *, active: bool = True) -> User:
    user = User(
        email=f"user{next(_seq)}@test.local",
        password_hash=_PASSWORD_HASH,
        role=role,
        is_active=active,
    )
    db.add(user)
    db.flush()
    return user


def make_customer(db: Session, name: str = "Acme Corp", country: str = "US") -> Customer:
    n = next(_seq)
    customer = Customer(name=name, email=f"buyer{n}@acme.example", country=country)
    db.add(customer)
    db.flush()
    return customer


def make_product(
    db: Session,
    *,
    name: str = "Widget",
    price: str = "10.00",
    stock: int = 100,
    threshold: int = 10,
    sku: str | None = None,
) -> Product:
    product = Product(
        sku=sku or f"T-{next(_seq):05d}",
        name=name,
        price=Decimal(price),
        stock_qty=stock,
        low_stock_threshold=threshold,
    )
    db.add(product)
    db.flush()
    return product


def make_order(
    db: Session,
    customer: Customer,
    lines: Sequence[tuple[Product, int]],
    *,
    status: str = "draft",
    created_at: datetime | None = None,
) -> Order:
    items = [OrderItem(product_id=p.id, qty=qty, unit_price=p.price) for p, qty in lines]
    order = Order(
        customer_id=customer.id,
        status=status,
        total=sum((i.unit_price * i.qty for i in items), Decimal("0.00")),
    )
    if created_at is not None:
        order.created_at = created_at
        order.updated_at = created_at
    order.items = items
    db.add(order)
    db.flush()
    return order
