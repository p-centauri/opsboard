"""Real races: parallel requests, each in its own committed transaction (no shared test
transaction), to prove row locks and version checks hold under concurrency."""

import threading
from collections.abc import Callable, Iterator
from functools import partial
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.db import get_engine
from app.main import app
from app.models import Order, Product
from tests.factories import PASSWORD, make_customer, make_order, make_product, make_user

RACERS = 2


@pytest.fixture
def clients(clean_db: Engine) -> Iterator[list[TestClient]]:
    app.dependency_overrides[get_engine] = lambda: clean_db
    with Session(clean_db) as db:
        user = make_user(db, "manager")
        db.commit()
        email = user.email
    pool = [TestClient(app, base_url="https://testserver") for _ in range(RACERS)]
    for c in pool:
        c.__enter__()
        assert c.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200
    yield pool
    for c in pool:
        c.__exit__(None, None, None)
    app.dependency_overrides.clear()


def _race(calls: list[Callable[[], Any]]) -> list[int]:
    """Start all calls at the same instant; return their status codes."""
    barrier = threading.Barrier(len(calls))
    statuses: list[int] = [0] * len(calls)

    def run(index: int) -> None:
        barrier.wait()
        statuses[index] = calls[index]().status_code

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(calls))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return sorted(statuses)


def test_last_unit_can_only_be_confirmed_once(clean_db: Engine, clients: list[TestClient]) -> None:
    with Session(clean_db) as db:
        product = make_product(db, stock=1)
        customer = make_customer(db)
        order_ids = [make_order(db, customer, [(product, 1)]).id for _ in range(RACERS)]
        db.commit()
        product_id = product.id

    statuses = _race(
        [
            partial(c.post, f"/orders/{oid}/transition", json={"to": "confirmed", "version": 1})
            for c, oid in zip(clients, order_ids, strict=True)
        ]
    )

    assert statuses == [200, 409]
    with Session(clean_db) as db:
        assert db.scalar(select(Product.stock_qty).where(Product.id == product_id)) == 0
        confirmed = db.scalars(select(Order.status).where(Order.id.in_(order_ids))).all()
        assert sorted(confirmed) == ["confirmed", "draft"]


def test_concurrent_edits_of_same_version_cannot_both_win(
    clean_db: Engine, clients: list[TestClient]
) -> None:
    with Session(clean_db) as db:
        product = make_product(db)
        order = make_order(db, make_customer(db), [(product, 1)])
        db.commit()
        order_id, product_id = order.id, product.id

    statuses = _race(
        [
            partial(
                c.patch,
                f"/orders/{order_id}",
                json={"version": 1, "items": [{"product_id": product_id, "qty": qty}]},
            )
            for c, qty in zip(clients, (5, 9), strict=True)
        ]
    )

    assert statuses == [200, 409]
    with Session(clean_db) as db:
        assert db.scalar(select(Order.version).where(Order.id == order_id)) == 2
