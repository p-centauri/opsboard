import csv
import io
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.services import export
from tests.factories import make_customer, make_order, make_product


@pytest.fixture
def viewer(login: Callable[[str], User]) -> User:
    return login("viewer")


def _rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def test_export_streams_filtered_orders_as_csv(
    client: TestClient, db: Session, viewer: User
) -> None:
    customer = make_customer(db, name="Acme, Inc.")
    product = make_product(db, price="3.00")
    shipped = make_order(
        db, customer, [(product, 2)], status="shipped", created_at=datetime(2026, 5, 1, tzinfo=UTC)
    )
    make_order(db, customer, [(product, 1)], status="draft")

    response = client.get("/orders/export.csv?status=shipped")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"].startswith('attachment; filename="orders-')
    assert _rows(response.text) == [
        list(export.HEADER),
        [
            shipped.number,
            "2026-05-01T00:00:00+00:00",
            "shipped",
            str(customer.id),
            "Acme, Inc.",
            "6.00",
        ],
    ]


def test_export_with_no_matches_is_header_only(client: TestClient, viewer: User) -> None:
    response = client.get("/orders/export.csv?q=nothing-matches")
    assert _rows(response.text) == [list(export.HEADER)]


def test_export_spans_multiple_fetch_batches(
    client: TestClient, db: Session, viewer: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(export, "FETCH_BATCH", 2)
    customer, product = make_customer(db), make_product(db)
    for _ in range(5):
        make_order(db, customer, [(product, 1)])

    rows = _rows(client.get("/orders/export.csv").text)

    assert len(rows) == 6


def test_export_neutralizes_spreadsheet_formulas(
    client: TestClient, db: Session, viewer: User
) -> None:
    customer = make_customer(db, name='=HYPERLINK("http://evil.example","x")')
    make_order(db, customer, [(make_product(db), 1)])

    name = _rows(client.get("/orders/export.csv").text)[1][4]

    assert name == '\'=HYPERLINK("http://evil.example","x")'


@pytest.mark.parametrize("value", ["=1+1", "+1", "-1", "@SUM(A1)", "\tx", "\rx"])
def test_safe_cell_prefixes_formula_starters(value: str) -> None:
    assert export.safe_cell(value) == f"'{value}"


def test_safe_cell_leaves_normal_text(value: str = "Acme Corp") -> None:
    assert export.safe_cell(value) == value


def test_export_refuses_instead_of_truncating(
    client: TestClient, db: Session, viewer: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.routers.orders.EXPORT_MAX_ROWS", 1)
    customer, product = make_customer(db), make_product(db)
    make_order(db, customer, [(product, 1)])
    make_order(db, customer, [(product, 1)])

    response = client.get("/orders/export.csv")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "export_too_large"
