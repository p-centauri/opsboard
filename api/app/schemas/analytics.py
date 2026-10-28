from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, PrivateAttr, model_validator

from app.models import OrderStatus
from app.schemas.common import InputModel, OutputModel

DEFAULT_DAYS = 30
MAX_DAYS = 1_096  # ~3 years; bounds the work a single request can ask for


class AnalyticsRange(InputModel):
    """Inclusive UTC date range. Defaults to the last 30 days, ending today."""

    date_from: date | None = None
    date_to: date | None = None

    _start: date = PrivateAttr()
    _end: date = PrivateAttr()

    @model_validator(mode="after")
    def _resolve(self) -> Self:
        end = self.date_to or datetime.now(UTC).date()
        start = self.date_from or end - timedelta(days=DEFAULT_DAYS - 1)
        if start > end:
            raise ValueError("date_from must be on or before date_to")
        if (end - start).days + 1 > MAX_DAYS:
            raise ValueError(f"Range can be at most {MAX_DAYS} days")
        self._start, self._end = start, end
        return self

    @property
    def start(self) -> date:
        return self._start

    @property
    def end(self) -> date:
        return self._end

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


class TrendParams(AnalyticsRange):
    interval: Literal["day", "week", "month"] = "day"


class TopProductsParams(AnalyticsRange):
    limit: int = Field(10, ge=1, le=50)


class PeriodMetrics(OutputModel):
    revenue: Decimal
    orders: int  # booked orders only (confirmed/shipped/delivered)
    avg_order_value: Decimal
    cancelled: int
    cancellation_rate: float  # cancelled / all orders, 0..1


class SummaryOut(OutputModel):
    date_from: date
    date_to: date
    current: PeriodMetrics
    previous: PeriodMetrics  # same-length period right before date_from
    low_stock_products: int


class TrendPoint(OutputModel):
    bucket: date
    revenue: Decimal
    orders: int


class TrendOut(OutputModel):
    interval: str
    points: list[TrendPoint]


class TopProduct(OutputModel):
    product_id: int
    sku: str
    name: str
    units: int
    revenue: Decimal


class StatusCount(OutputModel):
    status: OrderStatus
    count: int
