"""Dashboard aggregates. Each metric is one aggregate SQL query; Python only fills empty
buckets. Revenue and order counts include booked orders only (BOOKED_STATUSES). Dates are UTC."""

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.models import BOOKED_STATUSES, Order, OrderItem, OrderStatus, Product
from app.schemas.analytics import (
    AnalyticsRange,
    PeriodMetrics,
    StatusCount,
    SummaryOut,
    TopProduct,
    TrendOut,
    TrendParams,
    TrendPoint,
)
from app.services.orders import day_start

ZERO = Decimal("0.00")
BOOKED = Order.status.in_([s.value for s in BOOKED_STATUSES])
CANCELLED = Order.status == OrderStatus.CANCELLED


def _within(start: date, end: date) -> ColumnElement[bool]:
    return (Order.created_at >= day_start(start)) & (
        Order.created_at < day_start(end) + timedelta(days=1)
    )


def _period_columns(start: date, end: date) -> list[ColumnElement[Any]]:
    in_period = _within(start, end)
    return [
        func.coalesce(func.sum(Order.total).filter(in_period & BOOKED), ZERO),
        func.count().filter(in_period & BOOKED),
        func.count().filter(in_period & CANCELLED),
        func.count().filter(in_period),
    ]


def _metrics(revenue: Decimal, orders: int, cancelled: int, everything: int) -> PeriodMetrics:
    average = (revenue / orders).quantize(ZERO, ROUND_HALF_UP) if orders else ZERO
    return PeriodMetrics(
        revenue=revenue,
        orders=orders,
        avg_order_value=average,
        cancelled=cancelled,
        cancellation_rate=round(cancelled / everything, 4) if everything else 0.0,
    )


def summary(db: Session, rng: AnalyticsRange) -> SummaryOut:
    prev_end = rng.start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=rng.days - 1)
    row = db.execute(
        select(*_period_columns(rng.start, rng.end), *_period_columns(prev_start, prev_end)).where(
            _within(prev_start, rng.end)
        )
    ).one()
    low_stock = db.scalar(
        select(func.count()).where(Product.stock_qty <= Product.low_stock_threshold)
    )
    return SummaryOut(
        date_from=rng.start,
        date_to=rng.end,
        current=_metrics(*row[:4]),
        previous=_metrics(*row[4:]),
        low_stock_products=low_stock or 0,
    )


def bucket_start(day: date, interval: str) -> date:
    """Matches Postgres date_trunc: weeks start on Monday, months on the 1st."""
    if interval == "week":
        return day - timedelta(days=day.weekday())
    if interval == "month":
        return day.replace(day=1)
    return day


def _buckets(start: date, end: date, interval: str) -> list[date]:
    buckets: list[date] = []
    current = bucket_start(start, interval)
    while current <= end:
        buckets.append(current)
        if interval == "month":
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        else:
            current += timedelta(days=7 if interval == "week" else 1)
    return buckets


def revenue_trend(db: Session, params: TrendParams) -> TrendOut:
    bucket = func.date_trunc(params.interval, Order.created_at, "UTC").label("bucket")
    rows = db.execute(
        select(bucket, func.sum(Order.total), func.count())
        .where(_within(params.start, params.end), BOOKED)
        .group_by(bucket)
    ).all()
    found: dict[date, tuple[Decimal, int]] = {
        _as_date(b): (revenue, count) for b, revenue, count in rows
    }
    return TrendOut(
        interval=params.interval,
        points=[
            TrendPoint(
                bucket=b, revenue=found.get(b, (ZERO, 0))[0], orders=found.get(b, (ZERO, 0))[1]
            )
            for b in _buckets(params.start, params.end, params.interval)
        ],
    )


def _as_date(value: datetime | date) -> date:
    return value.date() if isinstance(value, datetime) else value


def top_products(db: Session, rng: AnalyticsRange, limit: int) -> list[TopProduct]:
    revenue = func.sum(OrderItem.qty * OrderItem.unit_price)
    rows = db.execute(
        select(Product.id, Product.sku, Product.name, func.sum(OrderItem.qty), revenue)
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(_within(rng.start, rng.end), BOOKED)
        .group_by(Product.id)
        .order_by(revenue.desc(), Product.id)
        .limit(limit)
    ).all()
    return [
        TopProduct(product_id=pid, sku=sku, name=name, units=units, revenue=rev)
        for pid, sku, name, units, rev in rows
    ]


def status_breakdown(db: Session, rng: AnalyticsRange) -> list[StatusCount]:
    # A comprehension, not dict(result): Result has .keys(), so dict() treats it as a mapping.
    counts = {
        status: count
        for status, count in db.execute(
            select(Order.status, func.count())
            .where(_within(rng.start, rng.end))
            .group_by(Order.status)
        )
    }
    return [StatusCount(status=s, count=counts.get(s.value, 0)) for s in OrderStatus]
