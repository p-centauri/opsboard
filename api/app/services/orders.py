"""Order rules: drafts are editable; status changes follow a fixed graph; confirming reserves
stock and cancelling a confirmed order releases it. Every write locks the order row and checks
its `version`, so concurrent edits fail with 409 instead of silently overwriting each other."""

from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, delete, func, or_, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app import audit
from app.errors import ApiError, not_found
from app.models import Customer, Order, OrderItem, OrderStatus, Product, User
from app.query import LIKE_ESCAPE, contains, sort_clause, starts_with
from app.schemas.orders import (
    CustomerRef,
    OrderCreate,
    OrderDetail,
    OrderFilters,
    OrderItemIn,
    OrderItemOut,
    OrderUpdate,
    TransitionIn,
)

S = OrderStatus
ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    S.DRAFT: frozenset({S.CONFIRMED, S.CANCELLED}),
    S.CONFIRMED: frozenset({S.SHIPPED, S.CANCELLED}),
    S.SHIPPED: frozenset({S.DELIVERED}),
    S.DELIVERED: frozenset(),
    S.CANCELLED: frozenset(),
}

SORTABLE = {
    "created_at": Order.created_at,
    "total": Order.total,
    "number": Order.number,
    "status": Order.status,
    "customer_name": Customer.name,
}


# --- Queries ------------------------------------------------------------------------------


def day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def filtered_orders(filters: OrderFilters) -> Select[Order, Customer]:
    """Orders joined with their customer, filtered. Dates are UTC days; date_to is inclusive."""
    stmt = select(Order, Customer).join(Customer, Customer.id == Order.customer_id)
    if filters.status:
        stmt = stmt.where(Order.status.in_([s.value for s in filters.status]))
    if filters.date_from:
        stmt = stmt.where(Order.created_at >= day_start(filters.date_from))
    if filters.date_to:
        stmt = stmt.where(Order.created_at < day_start(filters.date_to) + timedelta(days=1))
    if filters.customer_id:
        stmt = stmt.where(Order.customer_id == filters.customer_id)
    if filters.min_total is not None:
        stmt = stmt.where(Order.total >= filters.min_total)
    if filters.max_total is not None:
        stmt = stmt.where(Order.total <= filters.max_total)
    if filters.q:
        stmt = stmt.where(
            or_(
                Order.number.ilike(starts_with(filters.q), escape=LIKE_ESCAPE),
                Customer.name.ilike(contains(filters.q), escape=LIKE_ESCAPE),
            )
        )
    return stmt


def sorted_orders(filters: OrderFilters, sort: str) -> Select[Order, Customer]:
    return filtered_orders(filters).order_by(*sort_clause(sort, SORTABLE, Order.id))


def get_order_detail(db: Session, order_id: int) -> OrderDetail:
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(
            joinedload(Order.customer),
            selectinload(Order.items).joinedload(OrderItem.product),
        )
    )
    if order is None:
        raise not_found("Order")
    status = OrderStatus(order.status)
    return OrderDetail(
        id=order.id,
        number=order.number,
        customer=CustomerRef(id=order.customer.id, name=order.customer.name),
        status=status,
        total=order.total,
        created_at=order.created_at,
        updated_at=order.updated_at,
        version=order.version,
        items=[
            OrderItemOut(
                id=item.id,
                product_id=item.product_id,
                sku=item.product.sku,
                name=item.product.name,
                qty=item.qty,
                unit_price=item.unit_price,
                line_total=item.unit_price * item.qty,
            )
            for item in order.items
        ],
        allowed_transitions=sorted(ALLOWED_TRANSITIONS[status]),
        editable=status == OrderStatus.DRAFT,
    )


# --- Validation helpers -------------------------------------------------------------------


def _ensure_customer(db: Session, customer_id: int) -> None:
    if db.get(Customer, customer_id) is None:
        raise ApiError(
            422,
            "validation_error",
            "Some fields are invalid",
            {"customer_id": "Customer not found"},
        )


def _build_items(db: Session, items: Sequence[OrderItemIn]) -> tuple[list[OrderItem], Decimal]:
    """Order lines priced at the product's current price, plus the order total."""
    ids = [item.product_id for item in items]
    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(ids)))}
    missing = {
        f"items.{index}.product_id": "Product not found"
        for index, item in enumerate(items)
        if item.product_id not in products
    }
    if missing:
        raise ApiError(422, "validation_error", "Some fields are invalid", missing)

    lines = [
        OrderItem(
            product_id=item.product_id, qty=item.qty, unit_price=products[item.product_id].price
        )
        for item in items
    ]
    total = sum((line.unit_price * line.qty for line in lines), Decimal("0.00"))
    return lines, total


def _lock_order(db: Session, order_id: int, version: int) -> Order:
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .with_for_update()
        .options(selectinload(Order.items))
    )
    if order is None:
        raise not_found("Order")
    if order.version != version:
        raise ApiError(
            409,
            "stale_version",
            "This order was changed by someone else. Reload it and try again.",
        )
    return order


def _items_snapshot(items: Sequence[OrderItem]) -> list[dict[str, Any]]:
    return [{"product_id": i.product_id, "qty": i.qty, "unit_price": i.unit_price} for i in items]


def _bump(order: Order) -> None:
    order.version += 1
    order.updated_at = func.now()  # SQL expression: the DB sets the timestamp


# --- Stock --------------------------------------------------------------------------------


def _reserve_stock(db: Session, items: Sequence[OrderItem]) -> None:
    """Decrement stock for each line, atomically and only if enough is left. Rows are updated in
    product-id order so two orders sharing products can't deadlock each other."""
    index_by_product = {item.product_id: index for index, item in enumerate(items)}
    shortages: dict[str, str] = {}
    for item in sorted(items, key=lambda i: i.product_id):
        reserved = db.scalar(
            update(Product)
            .where(Product.id == item.product_id, Product.stock_qty >= item.qty)
            .values(stock_qty=Product.stock_qty - item.qty)
            .returning(Product.id)
        )
        if reserved is None:
            available = db.scalar(select(Product.stock_qty).where(Product.id == item.product_id))
            shortages[f"items.{index_by_product[item.product_id]}.qty"] = (
                f"Only {available} in stock"
            )
    if shortages:
        # The caller's transaction is rolled back, undoing any lines already reserved.
        raise ApiError(
            409, "insufficient_stock", "Not enough stock to confirm this order", shortages
        )


def _release_stock(db: Session, items: Sequence[OrderItem]) -> None:
    for item in sorted(items, key=lambda i: i.product_id):
        db.execute(
            update(Product)
            .where(Product.id == item.product_id)
            .values(stock_qty=Product.stock_qty + item.qty)
        )


# --- Commands -----------------------------------------------------------------------------


def create_order(db: Session, user: User, body: OrderCreate) -> int:
    _ensure_customer(db, body.customer_id)
    lines, total = _build_items(db, body.items)
    order = Order(customer_id=body.customer_id, status=OrderStatus.DRAFT.value, total=total)
    order.items = lines
    db.add(order)
    db.flush()
    audit.record(
        db,
        user.id,
        "order",
        order.id,
        "create",
        {"customer_id": body.customer_id, "items": _items_snapshot(lines), "total": total},
    )
    return order.id


def update_order(db: Session, user: User, order_id: int, body: OrderUpdate) -> None:
    order = _lock_order(db, order_id, body.version)
    if order.status != OrderStatus.DRAFT:
        raise ApiError(409, "order_not_editable", "Only draft orders can be edited")

    diff: dict[str, Any] = {}
    if body.customer_id is not None and body.customer_id != order.customer_id:
        _ensure_customer(db, body.customer_id)
        diff["customer_id"] = [order.customer_id, body.customer_id]
        order.customer_id = body.customer_id
    if body.items is not None:
        lines, total = _build_items(db, body.items)
        diff["items"] = [_items_snapshot(order.items), _items_snapshot(lines)]
        diff["total"] = [order.total, total]
        # Delete old lines before inserting new ones; (order_id, product_id) is unique.
        db.execute(delete(OrderItem).where(OrderItem.order_id == order.id))
        db.expire(order, ["items"])
        for line in lines:
            line.order_id = order.id
        db.add_all(lines)
        order.total = total

    _bump(order)
    db.flush()
    audit.record(db, user.id, "order", order.id, "update", diff)


def transition_order(db: Session, user: User, order_id: int, body: TransitionIn) -> None:
    order = _lock_order(db, order_id, body.version)
    current = OrderStatus(order.status)
    if body.to not in ALLOWED_TRANSITIONS[current]:
        raise ApiError(
            409,
            "invalid_transition",
            f"A {current.value} order can't be moved to {body.to.value}",
        )

    if body.to == OrderStatus.CONFIRMED:
        _reserve_stock(db, order.items)
    elif current == OrderStatus.CONFIRMED and body.to == OrderStatus.CANCELLED:
        _release_stock(db, order.items)

    order.status = body.to.value
    _bump(order)
    db.flush()
    audit.record(db, user.id, "order", order.id, "transition", {"status": [current, body.to]})
