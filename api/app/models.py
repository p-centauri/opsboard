"""Database schema. Integrity rules (uniqueness, ranges, allowed values) live in the
database as constraints, so no code path can bypass them."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

Money = Numeric(12, 2)


class Role(StrEnum):
    VIEWER = "viewer"
    MANAGER = "manager"
    ADMIN = "admin"


class OrderStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


def _in_check(column: str, enum: type[StrEnum]) -> str:
    values = ", ".join(f"'{member.value}'" for member in enum)
    return f"{column} IN ({values})"


class Base(DeclarativeBase):
    # Deterministic constraint names, so later migrations can alter/drop them by name.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def _id() -> Mapped[int]:
    # BY DEFAULT (not ALWAYS) so the seed can bulk-COPY explicit ids.
    return mapped_column(BigInteger, Identity(always=False), primary_key=True)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint(_in_check("role", Role), name="role_valid"),
    )

    id: Mapped[int] = _id()
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")
    created_at: Mapped[datetime] = _created_at()


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("char_length(country) = 2", name="country_iso2"),
        Index(
            "ix_customers_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = _id()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    created_at: Mapped[datetime] = _created_at()


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint("stock_qty >= 0", name="stock_non_negative"),
        CheckConstraint("low_stock_threshold >= 0", name="threshold_non_negative"),
    )

    id: Mapped[int] = _id()
    sku: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[Decimal] = mapped_column(Money, nullable=False)
    stock_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(_in_check("status", OrderStatus), name="status_valid"),
        CheckConstraint("total >= 0", name="total_non_negative"),
        CheckConstraint("version >= 1", name="version_positive"),
        Index("ix_orders_status_created_at", "status", "created_at"),
        Index("ix_orders_customer_id_created_at", "customer_id", "created_at"),
        Index("ix_orders_created_at", "created_at"),
    )

    id: Mapped[int] = _id()
    # Derived from the id, so it is unique without a check-then-insert race.
    number: Mapped[str] = mapped_column(
        String(16),
        Computed("'ORD-' || lpad(id::text, 7, '0')", persisted=True),
        unique=True,
    )
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    total: Mapped[Decimal] = mapped_column(Money, nullable=False)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Optimistic locking: every update must match and increment this.
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("qty > 0", name="qty_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        UniqueConstraint("order_id", "product_id"),
        Index("ix_order_items_product_id", "product_id"),
    )

    id: Mapped[int] = _id()
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    # Copied from the product when the order is placed; later price changes don't rewrite history.
    unit_price: Mapped[Decimal] = mapped_column(Money, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entity", "entity", "entity_id"),
        Index("ix_audit_log_created_at", "created_at"),
    )

    id: Mapped[int] = _id()
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # NULL = system
    entity: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    diff: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = _created_at()
