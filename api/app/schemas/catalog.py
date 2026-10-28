"""Customers and products."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.schemas.common import (
    Email,
    InputModel,
    Money,
    Name,
    OutputModel,
    PageParams,
    PatchModel,
    SearchText,
)

# Pydantic checks `pattern` before `to_upper`, so patterns accept either case.
Country = Annotated[str, StringConstraints(to_upper=True, pattern=r"^[A-Za-z]{2}$")]
Sku = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z0-9-]{1,32}$")
]
Quantity = Annotated[int, Field(ge=0, le=1_000_000)]


class CustomerIn(InputModel):
    name: Name
    email: Email
    country: Country


class CustomerPatch(PatchModel):
    name: Name | None = None
    email: Email | None = None
    country: Country | None = None


class CustomerOut(OutputModel):
    id: int
    name: str
    email: str
    country: str
    created_at: datetime


class CustomerDetail(CustomerOut):
    order_count: int
    lifetime_value: Decimal  # booked orders only (no drafts or cancelled)


class CustomerListParams(PageParams):
    q: SearchText | None = None
    sort: Literal["name", "-name", "created_at", "-created_at"] = "name"


class ProductIn(InputModel):
    sku: Sku
    name: Name
    price: Money
    stock_qty: Quantity
    low_stock_threshold: Quantity = 10


class ProductPatch(PatchModel):
    sku: Sku | None = None
    name: Name | None = None
    price: Money | None = None
    stock_qty: Quantity | None = None
    low_stock_threshold: Quantity | None = None


class ProductOut(OutputModel):
    id: int
    sku: str
    name: str
    price: Decimal
    stock_qty: int
    low_stock_threshold: int
    is_low_stock: bool


class ProductListParams(PageParams):
    q: SearchText | None = None
    low_stock: bool = False
    sort: Literal["name", "-name", "sku", "-sku", "price", "-price", "stock_qty", "-stock_qty"] = (
        "name"
    )
