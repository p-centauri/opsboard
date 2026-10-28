from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.analytics import MAX_DAYS
from app.services.analytics import _buckets, bucket_start
from tests.factories import make_customer, make_order, make_product


def at(day: str, hour: int = 12) -> datetime:
    return datetime.fromisoformat(day).replace(hour=hour, tzinfo=UTC)


@pytest.fixture
def data(db: Session, login: Callable[[str], User]) -> dict[str, Any]:
    """Previous period 2026-02-22..28, current period 2026-03-01..07."""
    login("viewer")
    customer = make_customer(db)
    cheap = make_product(db, name="Cheap", price="10.00")
    pricey = make_product(db, name="Pricey", price="100.00")
    # current period
    make_order(db, customer, [(cheap, 1)], status="delivered", created_at=at("2026-03-01"))
    make_order(
        db, customer, [(pricey, 1), (cheap, 2)], status="shipped", created_at=at("2026-03-01", 23)
    )
    make_order(db, customer, [(cheap, 5)], status="draft", created_at=at("2026-03-07"))
    make_order(db, customer, [(pricey, 9)], status="cancelled", created_at=at("2026-03-04"))
    # previous period
    make_order(db, customer, [(cheap, 3)], status="delivered", created_at=at("2026-02-25"))
    # outside both periods
    make_order(db, customer, [(pricey, 1)], status="delivered", created_at=at("2026-03-08", 0))
    return {"cheap": cheap, "pricey": pricey}


RANGE = "date_from=2026-03-01&date_to=2026-03-07"


def test_summary(client: TestClient, data: dict[str, Any]) -> None:
    body = client.get(f"/analytics/summary?{RANGE}").json()

    assert body["current"] == {
        "revenue": "130.00",  # 10 + 120; the draft and the cancelled order don't count
        "orders": 2,
        "avg_order_value": "65.00",
        "cancelled": 1,
        "cancellation_rate": 0.25,
    }
    assert body["previous"]["revenue"] == "30.00"
    assert body["previous"]["orders"] == 1
    assert (body["date_from"], body["date_to"]) == ("2026-03-01", "2026-03-07")


def test_summary_on_empty_range(client: TestClient, data: dict[str, Any]) -> None:
    body = client.get("/analytics/summary?date_from=2020-01-01&date_to=2020-01-02").json()
    assert body["current"] == {
        "revenue": "0.00",
        "orders": 0,
        "avg_order_value": "0.00",
        "cancelled": 0,
        "cancellation_rate": 0.0,
    }


def test_summary_counts_low_stock(client: TestClient, db: Session, data: dict[str, Any]) -> None:
    make_product(db, stock=1, threshold=5)
    assert client.get(f"/analytics/summary?{RANGE}").json()["low_stock_products"] == 1


def test_daily_trend_fills_empty_days_with_zero(client: TestClient, data: dict[str, Any]) -> None:
    points = client.get(f"/analytics/revenue-trend?{RANGE}").json()["points"]

    assert [p["bucket"] for p in points] == [f"2026-03-0{d}" for d in range(1, 8)]
    by_day = {p["bucket"]: (p["revenue"], p["orders"]) for p in points}
    assert by_day["2026-03-01"] == ("130.00", 2)  # 23:00 UTC stays on the 1st
    assert by_day["2026-03-02"] == ("0.00", 0)
    assert by_day["2026-03-04"] == ("0.00", 0)  # only a cancelled order that day
    assert by_day["2026-03-07"] == ("0.00", 0)  # only a draft that day


def test_weekly_and_monthly_trend(client: TestClient, data: dict[str, Any]) -> None:
    weekly = client.get(
        "/analytics/revenue-trend?interval=week&date_from=2026-02-23&date_to=2026-03-08"
    ).json()["points"]
    monthly = client.get(
        "/analytics/revenue-trend?interval=month&date_from=2026-02-01&date_to=2026-03-31"
    ).json()["points"]

    assert [(p["bucket"], p["revenue"]) for p in weekly] == [
        ("2026-02-23", "160.00"),  # Mon 23 Feb..Sun 1 Mar
        ("2026-03-02", "100.00"),  # the 8 Mar order; the 7 Mar draft doesn't count
    ]
    assert [(p["bucket"], p["revenue"]) for p in monthly] == [
        ("2026-02-01", "30.00"),
        ("2026-03-01", "230.00"),
    ]


def test_top_products(client: TestClient, data: dict[str, Any]) -> None:
    body = client.get(f"/analytics/top-products?{RANGE}&limit=5").json()
    assert [(p["name"], p["units"], p["revenue"]) for p in body] == [
        ("Pricey", 1, "100.00"),
        ("Cheap", 3, "30.00"),
    ]


def test_status_breakdown_includes_zero_statuses(client: TestClient, data: dict[str, Any]) -> None:
    body = client.get(f"/analytics/status-breakdown?{RANGE}").json()
    assert body == [
        {"status": "draft", "count": 1},
        {"status": "confirmed", "count": 0},
        {"status": "shipped", "count": 1},
        {"status": "delivered", "count": 1},
        {"status": "cancelled", "count": 1},
    ]


def test_default_range_is_last_30_days(client: TestClient, login: Callable[[str], User]) -> None:
    login("viewer")
    body = client.get("/analytics/summary").json()
    end = date.fromisoformat(body["date_to"])
    assert end == datetime.now(UTC).date()
    assert date.fromisoformat(body["date_from"]) == end - timedelta(days=29)


@pytest.mark.parametrize(
    "query",
    [
        "date_from=2026-03-05&date_to=2026-03-01",
        f"date_from=2020-01-01&date_to={(date(2020, 1, 1) + timedelta(days=MAX_DAYS)).isoformat()}",
        "interval=hour",
        "limit=0",
        "limit=51",
    ],
)
def test_invalid_analytics_params(
    client: TestClient, login: Callable[[str], User], query: str
) -> None:
    login("viewer")
    path = "/analytics/top-products" if "limit" in query else "/analytics/revenue-trend"
    assert client.get(f"{path}?{query}").status_code == 422


def test_bucket_helpers_match_postgres_date_trunc() -> None:
    assert bucket_start(date(2026, 3, 1), "week") == date(2026, 2, 23)  # Sunday -> Monday
    assert bucket_start(date(2026, 3, 18), "month") == date(2026, 3, 1)
    assert _buckets(date(2025, 11, 15), date(2026, 2, 1), "month") == [
        date(2025, 11, 1),
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    ]
