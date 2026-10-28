from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Customer, Product, User
from tests.factories import make_customer, make_order, make_product


@pytest.fixture
def manager(login: Callable[[str], User]) -> User:
    return login("manager")


@pytest.fixture
def customer(db: Session) -> Customer:
    return make_customer(db, name="Acme Corp")


@pytest.fixture
def bolt(db: Session) -> Product:
    return make_product(db, name="Bolt", price="2.50", stock=10)


@pytest.fixture
def nut(db: Session) -> Product:
    return make_product(db, name="Nut", price="0.40", stock=100)


def _create(client: TestClient, customer: Customer, lines: list[tuple[Product, int]]) -> Any:
    response = client.post(
        "/orders",
        json={
            "customer_id": customer.id,
            "items": [{"product_id": p.id, "qty": q} for p, q in lines],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _transition(client: TestClient, order: dict[str, Any], to: str) -> Any:
    return client.post(
        f"/orders/{order['id']}/transition", json={"to": to, "version": order["version"]}
    )


def _stock(db: Session, product: Product) -> int:
    db.expire_all()
    return db.scalar(select(Product.stock_qty).where(Product.id == product.id)) or 0


# --- Create -------------------------------------------------------------------------------


def test_create_order_computes_total_from_current_prices(
    client: TestClient, manager: User, customer: Customer, bolt: Product, nut: Product
) -> None:
    order = _create(client, customer, [(bolt, 3), (nut, 5)])

    assert order["status"] == "draft"
    assert order["version"] == 1
    assert order["number"] == f"ORD-{order['id']:07d}"
    assert order["total"] == "9.50"  # 3 x 2.50 + 5 x 0.40
    assert [(i["sku"], i["qty"], i["line_total"]) for i in order["items"]] == [
        (bolt.sku, 3, "7.50"),
        (nut.sku, 5, "2.00"),
    ]
    assert order["editable"] is True
    assert order["allowed_transitions"] == ["cancelled", "confirmed"]


def test_creating_a_draft_does_not_touch_stock(
    client: TestClient, db: Session, manager: User, customer: Customer, bolt: Product
) -> None:
    _create(client, customer, [(bolt, 4)])
    assert _stock(db, bolt) == 10


@pytest.mark.parametrize(
    ("items", "field"),
    [
        ([], "items"),
        ([{"product_id": 999_999, "qty": 1}], "items.0.product_id"),
        ([{"product_id": "abc", "qty": 1}], "items.0.product_id"),
        ([{"product_id": "BOLT", "qty": 0}], "items.0.qty"),
    ],
)
def test_create_order_item_validation(
    client: TestClient,
    manager: User,
    customer: Customer,
    bolt: Product,
    items: list[dict[str, Any]],
    field: str,
) -> None:
    for item in items:
        if item["product_id"] == "BOLT":
            item["product_id"] = bolt.id
    response = client.post("/orders", json={"customer_id": customer.id, "items": items})
    assert response.status_code == 422
    assert field in response.json()["error"]["fields"]


def test_create_order_rejects_duplicate_products(
    client: TestClient, manager: User, customer: Customer, bolt: Product
) -> None:
    items = [{"product_id": bolt.id, "qty": 1}, {"product_id": bolt.id, "qty": 2}]
    response = client.post("/orders", json={"customer_id": customer.id, "items": items})
    assert response.status_code == 422


def test_create_order_for_unknown_customer(
    client: TestClient, manager: User, bolt: Product
) -> None:
    response = client.post(
        "/orders", json={"customer_id": 999_999, "items": [{"product_id": bolt.id, "qty": 1}]}
    )
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"customer_id": "Customer not found"}


def test_client_cannot_set_status_or_total(
    client: TestClient, manager: User, customer: Customer, bolt: Product
) -> None:
    response = client.post(
        "/orders",
        json={
            "customer_id": customer.id,
            "items": [{"product_id": bolt.id, "qty": 1}],
            "status": "delivered",
            "total": "0.01",
        },
    )
    assert response.status_code == 422


# --- Update -------------------------------------------------------------------------------


def test_update_draft_replaces_items_and_bumps_version(
    client: TestClient,
    db: Session,
    manager: User,
    customer: Customer,
    bolt: Product,
    nut: Product,
) -> None:
    order = _create(client, customer, [(bolt, 1), (nut, 1)])

    response = client.patch(
        f"/orders/{order['id']}",
        json={"version": 1, "items": [{"product_id": nut.id, "qty": 10}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    assert body["total"] == "4.00"
    assert [(i["product_id"], i["qty"]) for i in body["items"]] == [(nut.id, 10)]
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "update")).one()
    assert entry.diff["total"] == ["2.90", "4.00"]


def test_update_can_keep_a_product_with_new_qty(
    client: TestClient, manager: User, customer: Customer, bolt: Product
) -> None:
    """Old and new lines share (order_id, product_id); the swap must not hit the unique key."""
    order = _create(client, customer, [(bolt, 1)])
    response = client.patch(
        f"/orders/{order['id']}", json={"version": 1, "items": [{"product_id": bolt.id, "qty": 2}]}
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["qty"] == 2


def test_update_with_stale_version_is_409(
    client: TestClient, manager: User, customer: Customer, bolt: Product
) -> None:
    order = _create(client, customer, [(bolt, 1)])
    client.patch(f"/orders/{order['id']}", json={"version": 1, "customer_id": customer.id})
    first = client.patch(
        f"/orders/{order['id']}", json={"version": 1, "items": [{"product_id": bolt.id, "qty": 9}]}
    )
    # The no-op customer change above still bumped the version to 2.
    assert first.status_code == 409
    assert first.json()["error"]["code"] == "stale_version"


def test_update_requires_something_to_change(
    client: TestClient, manager: User, customer: Customer, bolt: Product
) -> None:
    order = _create(client, customer, [(bolt, 1)])
    assert client.patch(f"/orders/{order['id']}", json={"version": 1}).status_code == 422


def test_confirmed_order_is_not_editable(
    client: TestClient, manager: User, customer: Customer, bolt: Product
) -> None:
    order = _create(client, customer, [(bolt, 1)])
    confirmed = _transition(client, order, "confirmed").json()

    response = client.patch(
        f"/orders/{order['id']}",
        json={"version": confirmed["version"], "items": [{"product_id": bolt.id, "qty": 5}]},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "order_not_editable"


def test_update_missing_order_is_404(client: TestClient, manager: User) -> None:
    response = client.patch("/orders/999999", json={"version": 1, "customer_id": 1})
    assert response.status_code == 404


# --- Transitions and stock ----------------------------------------------------------------


def test_full_lifecycle(
    client: TestClient, db: Session, manager: User, customer: Customer, bolt: Product
) -> None:
    order = _create(client, customer, [(bolt, 4)])
    for to in ("confirmed", "shipped", "delivered"):
        response = _transition(client, order, to)
        assert response.status_code == 200, response.text
        order = response.json()
        assert order["status"] == to

    assert order["version"] == 4
    assert order["allowed_transitions"] == []
    assert _stock(db, bolt) == 6  # reserved once, at confirmation
    actions = db.scalars(select(AuditLog.diff).where(AuditLog.action == "transition")).all()
    assert actions == [
        {"status": ["draft", "confirmed"]},
        {"status": ["confirmed", "shipped"]},
        {"status": ["shipped", "delivered"]},
    ]


@pytest.mark.parametrize(
    ("path", "illegal"),
    [
        ([], "shipped"),
        ([], "delivered"),
        (["confirmed"], "draft"),
        (["confirmed", "shipped"], "cancelled"),
        (["cancelled"], "confirmed"),
    ],
)
def test_illegal_transitions_are_409(
    client: TestClient,
    manager: User,
    customer: Customer,
    bolt: Product,
    path: list[str],
    illegal: str,
) -> None:
    order = _create(client, customer, [(bolt, 1)])
    for to in path:
        order = _transition(client, order, to).json()

    response = _transition(client, order, illegal)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_transition"


def test_confirm_with_insufficient_stock_reserves_nothing(
    client: TestClient,
    db: Session,
    manager: User,
    customer: Customer,
    bolt: Product,
    nut: Product,
) -> None:
    # nut (enough stock) is reserved first by id order, then bolt fails: nut must roll back.
    order = _create(client, customer, [(bolt, 11), (nut, 5)])

    response = _transition(client, order, "confirmed")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "insufficient_stock"
    assert error["fields"] == {"items.0.qty": "Only 10 in stock"}
    assert (_stock(db, bolt), _stock(db, nut)) == (10, 100)
    assert client.get(f"/orders/{order['id']}").json()["status"] == "draft"


def test_cancelling_confirmed_order_releases_stock(
    client: TestClient, db: Session, manager: User, customer: Customer, bolt: Product
) -> None:
    order = _transition(client, _create(client, customer, [(bolt, 7)]), "confirmed").json()
    assert _stock(db, bolt) == 3

    assert _transition(client, order, "cancelled").status_code == 200

    assert _stock(db, bolt) == 10


def test_cancelling_draft_leaves_stock_alone(
    client: TestClient, db: Session, manager: User, customer: Customer, bolt: Product
) -> None:
    order = _create(client, customer, [(bolt, 7)])
    assert _transition(client, order, "cancelled").status_code == 200
    assert _stock(db, bolt) == 10


def test_transition_with_stale_version_is_409(
    client: TestClient, manager: User, customer: Customer, bolt: Product
) -> None:
    order = _create(client, customer, [(bolt, 1)])
    _transition(client, order, "confirmed")
    response = _transition(client, order, "cancelled")  # still holds version 1
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stale_version"


def test_unknown_status_is_422(
    client: TestClient, manager: User, customer: Customer, bolt: Product
) -> None:
    order = _create(client, customer, [(bolt, 1)])
    assert _transition(client, order, "lost").status_code == 422


# --- List and filters ---------------------------------------------------------------------


@pytest.fixture
def catalog(db: Session) -> dict[str, Any]:
    def when(day: int) -> datetime:
        return datetime(2026, 3, day, 12, tzinfo=UTC)

    acme = make_customer(db, name="Acme Corp")
    globex = make_customer(db, name="Globex")
    widget = make_product(db, price="10.00")
    orders = {
        "a": make_order(db, acme, [(widget, 1)], status="draft", created_at=when(1)),
        "b": make_order(db, acme, [(widget, 5)], status="shipped", created_at=when(2)),
        "c": make_order(db, globex, [(widget, 20)], status="cancelled", created_at=when(3)),
        "d": make_order(db, globex, [(widget, 3)], status="shipped", created_at=when(4)),
    }
    return {"acme": acme, "globex": globex, "orders": orders}


def _ids(client: TestClient, query: str) -> list[int]:
    response = client.get(f"/orders?{query}")
    assert response.status_code == 200, response.text
    return [o["id"] for o in response.json()["items"]]


def test_order_filters(client: TestClient, manager: User, catalog: dict[str, Any]) -> None:
    o = {k: v.id for k, v in catalog["orders"].items()}
    acme = catalog["acme"].id

    assert _ids(client, "sort=created_at") == [o["a"], o["b"], o["c"], o["d"]]
    assert _ids(client, "status=shipped&status=draft&sort=created_at") == [o["a"], o["b"], o["d"]]
    assert _ids(client, "date_from=2026-03-02&date_to=2026-03-03&sort=created_at") == [
        o["b"],
        o["c"],
    ]
    assert _ids(client, f"customer_id={acme}&sort=created_at") == [o["a"], o["b"]]
    assert _ids(client, "min_total=30&max_total=50") == [o["d"], o["b"]]
    assert _ids(client, "q=glob&sort=created_at") == [o["c"], o["d"]]
    assert _ids(client, f"q=ord-{o['c']:07d}") == [o["c"]]
    assert _ids(client, "sort=-total") == [o["c"], o["b"], o["d"], o["a"]]


def test_order_list_shape(client: TestClient, manager: User, catalog: dict[str, Any]) -> None:
    body = client.get("/orders?page_size=1").json()
    assert body["total"] == 4
    assert len(body["items"]) == 1
    assert body["items"][0]["customer"] == {"id": catalog["globex"].id, "name": "Globex"}


@pytest.mark.parametrize(
    "query",
    [
        "date_from=2026-03-05&date_to=2026-03-01",
        "min_total=50&max_total=10",
        "status=lost",
        "sort=password",
        "page_size=101",
        "page=0",
    ],
)
def test_invalid_list_params_are_422(client: TestClient, manager: User, query: str) -> None:
    assert client.get(f"/orders?{query}").status_code == 422


def test_get_order_404(client: TestClient, manager: User) -> None:
    assert client.get("/orders/999999").status_code == 404
