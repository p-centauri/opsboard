"""Customers and products endpoints."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, User
from tests.factories import make_customer, make_order, make_product


@pytest.fixture
def manager(login: Callable[[str], User]) -> User:
    return login("manager")


# --- Customers ----------------------------------------------------------------------------


def test_create_customer_normalizes_input_and_audits(
    client: TestClient, db: Session, manager: User
) -> None:
    response = client.post(
        "/customers", json={"name": "  Globex  ", "email": "Sales@Globex.example", "country": "de"}
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["name"], body["email"], body["country"]) == (
        "Globex",
        "sales@globex.example",
        "DE",
    )
    assert (body["order_count"], body["lifetime_value"]) == (0, "0")
    entry = db.scalars(select(AuditLog).where(AuditLog.entity == "customer")).one()
    assert (entry.user_id, entry.entity_id, entry.action) == (manager.id, body["id"], "create")


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"name": "", "email": "a@b.example", "country": "US"}, "name"),
        ({"name": "A", "email": "not-an-email", "country": "US"}, "email"),
        ({"name": "A", "email": "a@b.example", "country": "USA"}, "country"),
        ({"name": "A", "email": "a@b.example"}, "country"),
    ],
)
def test_create_customer_validation(
    client: TestClient, manager: User, payload: dict[str, str], field: str
) -> None:
    response = client.post("/customers", json=payload)
    assert response.status_code == 422
    assert field in response.json()["error"]["fields"]


def test_customer_lifetime_value_counts_booked_orders_only(
    client: TestClient, db: Session, manager: User
) -> None:
    customer = make_customer(db)
    product = make_product(db, price="25.00")
    make_order(db, customer, [(product, 2)], status="delivered")
    make_order(db, customer, [(product, 10)], status="cancelled")
    make_order(db, customer, [(product, 4)], status="draft")

    body = client.get(f"/customers/{customer.id}").json()

    assert body["order_count"] == 3
    assert body["lifetime_value"] == "50.00"


def test_get_missing_customer_is_404(client: TestClient, manager: User) -> None:
    response = client.get("/customers/999999")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Customer not found"}}


def test_patch_customer_changes_only_sent_fields(
    client: TestClient, db: Session, manager: User
) -> None:
    customer = make_customer(db, name="Old Name", country="US")

    response = client.patch(f"/customers/{customer.id}", json={"name": "New Name"})

    assert response.status_code == 200
    assert (response.json()["name"], response.json()["country"]) == ("New Name", "US")
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "update")).one()
    assert entry.diff == {"name": ["Old Name", "New Name"]}


def test_patch_rejects_null_and_unknown_fields(
    client: TestClient, db: Session, manager: User
) -> None:
    customer = make_customer(db)
    assert client.patch(f"/customers/{customer.id}", json={"name": None}).status_code == 422
    assert client.patch(f"/customers/{customer.id}", json={"id": 5}).status_code == 422


def test_noop_patch_writes_no_audit_entry(client: TestClient, db: Session, manager: User) -> None:
    customer = make_customer(db, name="Same")
    assert client.patch(f"/customers/{customer.id}", json={"name": "Same"}).status_code == 200
    assert db.scalars(select(AuditLog)).all() == []


def test_customer_search_matches_name_or_email(
    client: TestClient, db: Session, manager: User
) -> None:
    make_customer(db, name="Initech")
    make_customer(db, name="Umbrella")

    names = [c["name"] for c in client.get("/customers?q=inite").json()["items"]]

    assert names == ["Initech"]


def test_search_treats_wildcards_literally(client: TestClient, db: Session, manager: User) -> None:
    make_customer(db, name="100% Organic")
    make_customer(db, name="1000 Organics")
    make_customer(db, name="A_B Corp")
    make_customer(db, name="AXB Corp")

    percent = [c["name"] for c in client.get("/customers", params={"q": "100%"}).json()["items"]]
    underscore = [c["name"] for c in client.get("/customers", params={"q": "A_B"}).json()["items"]]

    assert percent == ["100% Organic"]
    assert underscore == ["A_B Corp"]


def test_customer_list_pagination_and_sort(client: TestClient, db: Session, manager: User) -> None:
    for name in ("Delta", "Alpha", "Charlie", "Bravo"):
        make_customer(db, name=name)

    first = client.get("/customers?page=1&page_size=3&sort=name").json()
    second = client.get("/customers?page=2&page_size=3&sort=name").json()
    descending = client.get("/customers?sort=-name").json()

    assert [c["name"] for c in first["items"]] == ["Alpha", "Bravo", "Charlie"]
    assert [c["name"] for c in second["items"]] == ["Delta"]
    assert (first["total"], first["page"], first["page_size"]) == (4, 1, 3)
    assert descending["items"][0]["name"] == "Delta"


# --- Products -----------------------------------------------------------------------------


def test_create_product(client: TestClient, manager: User) -> None:
    response = client.post(
        "/products",
        json={
            "sku": " ab-12 ",
            "name": "Bolt",
            "price": "1.50",
            "stock_qty": 3,
            "low_stock_threshold": 5,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert (body["sku"], body["price"], body["is_low_stock"]) == ("AB-12", "1.50", True)


def test_duplicate_sku_is_409_on_the_sku_field(
    client: TestClient, db: Session, manager: User
) -> None:
    make_product(db, sku="DUP-1")
    response = client.post(
        "/products", json={"sku": "dup-1", "name": "Other", "price": "1.00", "stock_qty": 1}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert "sku" in response.json()["error"]["fields"]


def test_renaming_sku_onto_existing_one_is_409(
    client: TestClient, db: Session, manager: User
) -> None:
    make_product(db, sku="TAKEN")
    product = make_product(db, sku="FREE")
    response = client.patch(f"/products/{product.id}", json={"sku": "TAKEN"})
    assert response.status_code == 409


@pytest.mark.parametrize(
    ("field", "value"),
    [("price", "-1.00"), ("price", "1.001"), ("stock_qty", -1), ("price", "abc")],
)
def test_product_validation(
    client: TestClient, db: Session, manager: User, field: str, value: object
) -> None:
    product = make_product(db)
    response = client.patch(f"/products/{product.id}", json={field: value})
    assert response.status_code == 422
    assert field in response.json()["error"]["fields"]


def test_low_stock_filter(client: TestClient, db: Session, manager: User) -> None:
    make_product(db, name="Plenty", stock=50, threshold=10)
    make_product(db, name="Edge", stock=10, threshold=10)
    make_product(db, name="Out", stock=0, threshold=5)

    names = {p["name"] for p in client.get("/products?low_stock=true").json()["items"]}

    assert names == {"Edge", "Out"}


def test_product_price_change_does_not_rewrite_existing_orders(
    client: TestClient, db: Session, manager: User
) -> None:
    product = make_product(db, price="10.00")
    order = make_order(db, make_customer(db), [(product, 1)], created_at=datetime.now(UTC))

    client.patch(f"/products/{product.id}", json={"price": "99.00"})

    detail = client.get(f"/orders/{order.id}").json()
    assert detail["items"][0]["unit_price"] == "10.00"
    assert Decimal(detail["total"]) == Decimal("10.00")
