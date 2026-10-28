from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from app.models import OrderStatus
from app.schemas.common import (
    DateRange,
    InputModel,
    Money,
    OutputModel,
    PageParams,
    SearchText,
)

MAX_ITEMS = 100


class OrderItemIn(InputModel):
    product_id: int = Field(ge=1)
    qty: int = Field(ge=1, le=10_000)


Items = Annotated[list[OrderItemIn], Field(min_length=1, max_length=MAX_ITEMS)]


def _ensure_unique_products(items: list[OrderItemIn] | None) -> None:
    if items is None:
        return
    ids = [item.product_id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Each product can appear only once; adjust qty instead")


class OrderCreate(InputModel):
    customer_id: int = Field(ge=1)
    items: Items

    @model_validator(mode="after")
    def _unique(self) -> Self:
        _ensure_unique_products(self.items)
        return self


class OrderUpdate(InputModel):
    version: int = Field(ge=1)
    customer_id: int | None = Field(None, ge=1)
    items: Items | None = None

    @model_validator(mode="after")
    def _valid(self) -> Self:
        _ensure_unique_products(self.items)
        if self.customer_id is None and self.items is None:
            raise ValueError("Nothing to update: send customer_id and/or items")
        return self


class TransitionIn(InputModel):
    to: OrderStatus
    version: int = Field(ge=1)


SortField = Literal[
    "created_at", "-created_at", "total", "-total", "number", "-number",
    "status", "-status", "customer_name", "-customer_name",
]  # fmt: skip


class OrderFilters(DateRange):
    status: list[OrderStatus] = Field(default_factory=list, max_length=len(OrderStatus))
    customer_id: int | None = Field(None, ge=1)
    min_total: Money | None = None
    max_total: Money | None = None
    q: SearchText | None = None  # order number prefix or customer name

    @model_validator(mode="after")
    def _total_range(self) -> Self:
        low, high = self.min_total, self.max_total
        if low is not None and high is not None and low > high:
            raise ValueError("min_total must be less than or equal to max_total")
        return self


class OrderListParams(OrderFilters, PageParams):
    sort: SortField = "-created_at"


class CustomerRef(OutputModel):
    id: int
    name: str


class OrderSummary(OutputModel):
    id: int
    number: str
    customer: CustomerRef
    status: OrderStatus
    total: Decimal
    created_at: datetime
    updated_at: datetime


class OrderItemOut(OutputModel):
    id: int
    product_id: int
    sku: str
    name: str
    qty: int
    unit_price: Decimal
    line_total: Decimal


class OrderDetail(OrderSummary):
    version: int
    items: list[OrderItemOut]
    allowed_transitions: list[OrderStatus]
    editable: bool
