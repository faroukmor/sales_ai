from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.auth import current_user, require_csrf
from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import Product, User, UserSession

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(user: Annotated[User, Depends(current_user)]) -> User:
    configured_email = get_settings().admin_email.strip().lower()
    if not configured_email or user.email.strip().lower() != configured_email:
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


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

    @field_validator("name", "category", "currency")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("brand", "description", "url")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


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

    @field_validator("name", "category", "currency")
    @classmethod
    def strip_required(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("brand", "description", "url")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


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
    }


@router.get("/me")
def admin_me(_: Annotated[User, Depends(require_admin)]):
    return {"is_admin": True}


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
        clauses.append(or_(Product.name.icontains(term), Product.brand.icontains(term), Product.category.icontains(term)))
    if category.strip():
        clauses.append(func.lower(Product.category) == category.strip().lower())
    total = db.scalar(select(func.count(Product.id)).where(*clauses)) or 0
    rows = db.scalars(
        select(Product).where(*clauses).order_by(Product.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
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
    values = body.model_dump()
    if values["stock_quantity"] is not None:
        values["in_stock"] = values["stock_quantity"] > 0
    product = Product(**values)
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
    values = body.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(product, key, value)
    if "stock_quantity" in values and values["stock_quantity"] is not None:
        product.in_stock = values["stock_quantity"] > 0
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
