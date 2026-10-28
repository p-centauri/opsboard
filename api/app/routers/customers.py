from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select

from app import audit
from app.crud import apply_changes, flush_or_conflict
from app.deps import Db, Manager, Viewer
from app.errors import not_found
from app.models import BOOKED_STATUSES, Customer, Order
from app.query import LIKE_ESCAPE, contains, paginate, sort_clause
from app.schemas.catalog import (
    CustomerDetail,
    CustomerIn,
    CustomerListParams,
    CustomerOut,
    CustomerPatch,
)
from app.schemas.common import Page

router = APIRouter(prefix="/customers", tags=["customers"])

SORTABLE = {"name": Customer.name, "created_at": Customer.created_at}


def _detail(db: Db, customer: Customer) -> CustomerDetail:
    order_count, lifetime_value = db.execute(
        select(
            func.count(),
            func.coalesce(
                func.sum(Order.total).filter(Order.status.in_(BOOKED_STATUSES)), Decimal(0)
            ),
        ).where(Order.customer_id == customer.id)
    ).one()
    return CustomerDetail(
        **CustomerOut.model_validate(customer).model_dump(),
        order_count=order_count,
        lifetime_value=lifetime_value,
    )


@router.get("")
def list_customers(
    params: Annotated[CustomerListParams, Query()], db: Db, _: Viewer
) -> Page[CustomerOut]:
    stmt = select(Customer).order_by(*sort_clause(params.sort, SORTABLE, Customer.id))
    if params.q:
        pattern = contains(params.q)
        stmt = stmt.where(
            or_(
                Customer.name.ilike(pattern, escape=LIKE_ESCAPE),
                Customer.email.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    rows, total = paginate(db, stmt, params)
    return Page(
        items=[CustomerOut.model_validate(row.Customer) for row in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{customer_id}")
def get_customer(customer_id: int, db: Db, _: Viewer) -> CustomerDetail:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise not_found("Customer")
    return _detail(db, customer)


@router.post("", status_code=201)
def create_customer(body: CustomerIn, db: Db, user: Manager) -> CustomerDetail:
    customer = Customer(**body.model_dump())
    db.add(customer)
    flush_or_conflict(db)
    audit.record(db, user.id, "customer", customer.id, "create", body.model_dump())
    db.commit()
    return _detail(db, customer)


@router.patch("/{customer_id}")
def update_customer(customer_id: int, body: CustomerPatch, db: Db, user: Manager) -> CustomerDetail:
    customer = db.get(Customer, customer_id, with_for_update=True)
    if customer is None:
        raise not_found("Customer")
    diff = apply_changes(customer, body.changes())
    if diff:
        flush_or_conflict(db)
        audit.record(db, user.id, "customer", customer.id, "update", diff)
        db.commit()
    return _detail(db, customer)
