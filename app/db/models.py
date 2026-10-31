from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_nonnegative"),
        CheckConstraint("length(currency) = 3", name="ck_products_currency_length"),
        Index("ix_products_category_price", "category", "price"),
        Index("ix_products_category_in_stock", "category", "in_stock"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="DZD")
    in_stock: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_test_data: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )

    specs: Mapped[list[ProductSpec]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by="ProductSpec.key",
    )
    promotions: Mapped[list[Promotion]] = relationship(
        back_populates="product",
        passive_deletes=True,
        lazy="selectin",
        order_by="Promotion.id",
    )


class ProductSpec(Base):
    __tablename__ = "product_specs"
    __table_args__ = (
        UniqueConstraint("product_id", "key", name="uq_product_specs_product_key"),
        CheckConstraint(
            "value_text IS NOT NULL OR value_num IS NOT NULL",
            name="ck_product_specs_has_value",
        ),
        Index("ix_product_specs_key_value_num", "key", "value_num"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    value_num: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    product: Mapped[Product] = relationship(back_populates="specs")


class Promotion(Base):
    __tablename__ = "promotions"
    __table_args__ = (
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR starts_at <= ends_at",
            name="ck_promotions_valid_interval",
        ),
        Index("ix_promotions_validity", "starts_at", "ends_at"),
        Index("ix_promotions_category_validity", "category", "starts_at", "ends_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    is_test_data: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )

    product: Mapped[Product | None] = relationship(back_populates="promotions")
