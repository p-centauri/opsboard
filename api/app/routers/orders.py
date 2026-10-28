from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.deps import Db, Manager, Viewer
from app.errors import ApiError
from app.query import paginate
from app.schemas.common import Page
from app.schemas.orders import (
    CustomerRef,
    OrderCreate,
    OrderDetail,
    OrderFilters,
    OrderListParams,
    OrderSummary,
    OrderUpdate,
    TransitionIn,
)
from app.services import orders
from app.services.export import EXPORT_MAX_ROWS, stream_orders_csv

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("")
def list_orders(
    params: Annotated[OrderListParams, Query()], db: Db, _: Viewer
) -> Page[OrderSummary]:
    rows, total = paginate(db, orders.sorted_orders(params, params.sort), params)
    items = [
        OrderSummary(
            id=order.id,
            number=order.number,
            customer=CustomerRef(id=customer.id, name=customer.name),
            status=order.status,
            total=order.total,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        for order, customer in rows
    ]
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


# Declared before /{order_id} so "export.csv" isn't parsed as an order id.
@router.get("/export.csv")
def export_orders(
    filters: Annotated[OrderFilters, Query()], db: Db, _: Viewer
) -> StreamingResponse:
    stmt = orders.sorted_orders(filters, "-created_at")
    matching = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    if matching > EXPORT_MAX_ROWS:
        # Refuse rather than silently truncate: a partial export looks complete.
        raise ApiError(
            422,
            "export_too_large",
            f"{matching} orders match; narrow the filters to at most {EXPORT_MAX_ROWS}.",
        )
    filename = f"orders-{datetime.now(UTC):%Y%m%d-%H%M%S}.csv"
    return StreamingResponse(
        stream_orders_csv(db, stmt),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{order_id}")
def get_order(order_id: int, db: Db, _: Viewer) -> OrderDetail:
    return orders.get_order_detail(db, order_id)


@router.post("", status_code=201)
def create_order(body: OrderCreate, db: Db, user: Manager) -> OrderDetail:
    order_id = orders.create_order(db, user, body)
    db.commit()
    return orders.get_order_detail(db, order_id)


@router.patch("/{order_id}")
def update_order(order_id: int, body: OrderUpdate, db: Db, user: Manager) -> OrderDetail:
    orders.update_order(db, user, order_id, body)
    db.commit()
    return orders.get_order_detail(db, order_id)


@router.post("/{order_id}/transition")
def transition_order(order_id: int, body: TransitionIn, db: Db, user: Manager) -> OrderDetail:
    orders.transition_order(db, user, order_id, body)
    db.commit()
    return orders.get_order_detail(db, order_id)
