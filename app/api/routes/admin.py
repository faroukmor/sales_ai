from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import current_user, is_admin_user, require_csrf
from app.core.catalog_schema import catalog_schema
from app.db.database import get_db
from app.db.models import Product, ProductSpec, User, UserSession
from app.services.query_validator import QueryValidator

router = APIRouter(prefix="/api/admin", tags=["admin"])

NON_NULLABLE_PRODUCT_FIELDS = {"name", "category", "currency", "is_test_data"}


def require_admin(user: Annotated[User, Depends(current_user)]) -> User:
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


def _clean_url(value: str | None) -> str | None:
    """Only http(s) links are accepted: other schemes (javascript:, data:) could run script
    when the link is rendered in the store or in the assistant."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not value.lower().startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return value


class SpecIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,99}$")
    value_text: str | None = Field(default=None, max_length=255)
    value_num: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    unit: str | None = Field(default=None, max_length=50)

    @field_validator("value_text", "unit")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None

    @model_validator(mode="after")
    def needs_a_value(self) -> SpecIn:
        if self.value_text is None and self.value_num is None:
            raise ValueError(f"Specification '{self.key}' needs a value")
        return self


def _unique_spec_keys(specs: list[SpecIn] | None) -> list[SpecIn] | None:
    if specs is not None:
        keys = [item.key for item in specs]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise ValueError(f"Duplicate specifications: {', '.join(duplicates)}")
    return specs


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    category: str = Field(min_length=2, max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="DZD", min_length=3, max_length=3)
    in_stock: bool | None = True
    stock_quantity: int | None = Field(default=0, ge=0)
    url: str | None = Field(default=None, max_length=2000)
    is_test_data: bool = False
    specs: list[SpecIn] = Field(default_factory=list, max_length=60)

    @field_validator("name", "category", "currency")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("brand", "description")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None

    @field_validator("url")
    @classmethod
    def check_url(cls, value: str | None) -> str | None:
        return _clean_url(value)

    @field_validator("specs")
    @classmethod
    def check_specs(cls, value: list[SpecIn]) -> list[SpecIn]:
        return _unique_spec_keys(value) or []


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    category: str | None = Field(default=None, min_length=2, max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    in_stock: bool | None = None
    stock_quantity: int | None = Field(default=None, ge=0)
    url: str | None = Field(default=None, max_length=2000)
    is_test_data: bool | None = None
    # When present, the product's specifications are replaced by exactly this list.
    specs: list[SpecIn] | None = Field(default=None, max_length=60)

    @field_validator("name", "category", "currency")
    @classmethod
    def strip_required(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("brand", "description")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None

    @field_validator("url")
    @classmethod
    def check_url(cls, value: str | None) -> str | None:
        return _clean_url(value)

    @field_validator("specs")
    @classmethod
    def check_specs(cls, value: list[SpecIn] | None) -> list[SpecIn] | None:
        return _unique_spec_keys(value)


def serialize_product(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "brand": product.brand,
        "description": product.description,
        "price": product.price,
        "currency": product.currency,
        "in_stock": product.in_stock,
        "stock_quantity": product.stock_quantity,
        "url": product.url,
        "is_test_data": product.is_test_data,
        "specs": [
            {"key": s.key, "value_text": s.value_text, "value_num": s.value_num, "unit": s.unit}
            for s in product.specs
        ],
    }


def sync_specs(product: Product, specs: list[SpecIn]) -> None:
    """Make the product's specs equal to ``specs`` (update in place, add new, drop missing).

    Updating in place matters: replacing the collection would INSERT a re-added key before the
    old row is DELETEd and trip the (product_id, key) unique constraint.
    """
    existing = {row.key: row for row in product.specs}
    wanted = {item.key: item for item in specs}
    for key, row in existing.items():
        if key not in wanted:
            product.specs.remove(row)
    for key, item in wanted.items():
        row = existing.get(key)
        if row is None:
            product.specs.append(
                ProductSpec(
                    key=key, value_text=item.value_text, value_num=item.value_num, unit=item.unit
                )
            )
        else:
            row.value_text, row.value_num, row.unit = item.value_text, item.value_num, item.unit


@router.get("/me")
def admin_me(_: Annotated[User, Depends(require_admin)]):
    return {"is_admin": True}


@router.get("/catalog-schema")
def get_catalog_schema(_: Annotated[User, Depends(require_admin)]):
    """Product types and their specification fields for the admin product form."""
    return catalog_schema(QueryValidator.DEFAULT_CATEGORIES)


@router.get("/products")
def list_products(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    q: str = "",
    category: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    clauses = []
    if q.strip():
        term = q.strip()
        clauses.append(
            or_(
                Product.name.icontains(term, autoescape=True),
                Product.brand.icontains(term, autoescape=True),
                Product.category.icontains(term, autoescape=True),
            )
        )
    if category.strip():
        clauses.append(func.lower(Product.category) == category.strip().lower())
    total = db.scalar(select(func.count(Product.id)).where(*clauses)) or 0
    rows = db.scalars(
        select(Product)
        .where(*clauses)
        .order_by(Product.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    categories = db.scalars(select(Product.category).distinct().order_by(Product.category)).all()
    return {
        "items": [serialize_product(p) for p in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "categories": categories,
    }


@router.post("/products", status_code=status.HTTP_201_CREATED)
def create_product(
    body: ProductCreate,
    _admin: Annotated[User, Depends(require_admin)],
    _: Annotated[UserSession, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db)],
):
    values = body.model_dump(exclude={"specs"})
    if values["stock_quantity"] is not None:
        values["in_stock"] = values["stock_quantity"] > 0
    product = Product(**values)
    sync_specs(product, body.specs)
    db.add(product)
    db.commit()
    db.refresh(product)
    return serialize_product(product)


@router.patch("/products/{product_id}")
def update_product(
    product_id: int,
    body: ProductUpdate,
    _admin: Annotated[User, Depends(require_admin)],
    _: Annotated[UserSession, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db)],
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    values = body.model_dump(exclude_unset=True, exclude={"specs"})
    for key, value in values.items():
        if value is None and key in NON_NULLABLE_PRODUCT_FIELDS:
            raise HTTPException(status_code=422, detail=f"'{key}' cannot be empty")
        setattr(product, key, value)
    if "stock_quantity" in values and values["stock_quantity"] is not None:
        product.in_stock = values["stock_quantity"] > 0
    if body.specs is not None:
        sync_specs(product, body.specs)
    db.commit()
    db.refresh(product)
    return serialize_product(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    _admin: Annotated[User, Depends(require_admin)],
    _: Annotated[UserSession, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db)],
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This product is referenced by an existing cart or order and cannot be deleted.",
        ) from None
