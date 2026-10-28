from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from app import audit
from app.crud import apply_changes, flush_or_conflict
from app.deps import Db, Manager, Viewer
from app.errors import not_found
from app.models import Product
from app.query import LIKE_ESCAPE, contains, paginate, sort_clause
from app.schemas.catalog import ProductIn, ProductListParams, ProductOut, ProductPatch
from app.schemas.common import Page

router = APIRouter(prefix="/products", tags=["products"])

SORTABLE = {
    "name": Product.name,
    "sku": Product.sku,
    "price": Product.price,
    "stock_qty": Product.stock_qty,
}


@router.get("")
def list_products(
    params: Annotated[ProductListParams, Query()], db: Db, _: Viewer
) -> Page[ProductOut]:
    stmt = select(Product).order_by(*sort_clause(params.sort, SORTABLE, Product.id))
    if params.q:
        pattern = contains(params.q)
        stmt = stmt.where(
            or_(
                Product.name.ilike(pattern, escape=LIKE_ESCAPE),
                Product.sku.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    if params.low_stock:
        stmt = stmt.where(Product.stock_qty <= Product.low_stock_threshold)
    rows, total = paginate(db, stmt, params)
    return Page(
        items=[ProductOut.model_validate(row.Product) for row in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{product_id}")
def get_product(product_id: int, db: Db, _: Viewer) -> ProductOut:
    product = db.get(Product, product_id)
    if product is None:
        raise not_found("Product")
    return ProductOut.model_validate(product)


@router.post("", status_code=201)
def create_product(body: ProductIn, db: Db, user: Manager) -> ProductOut:
    product = Product(**body.model_dump())
    db.add(product)
    flush_or_conflict(db)
    audit.record(db, user.id, "product", product.id, "create", body.model_dump())
    db.commit()
    return ProductOut.model_validate(product)


@router.patch("/{product_id}")
def update_product(product_id: int, body: ProductPatch, db: Db, user: Manager) -> ProductOut:
    product = db.get(Product, product_id, with_for_update=True)
    if product is None:
        raise not_found("Product")
    diff = apply_changes(product, body.changes())
    if diff:
        flush_or_conflict(db)
        audit.record(db, user.id, "product", product.id, "update", diff)
        db.commit()
    return ProductOut.model_validate(product)
