from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.auth import current_user, require_csrf
from app.db.database import get_db
from app.db.models import Cart, CartItem, Order, OrderItem, Product, Promotion, User, UserSession

router = APIRouter(prefix="/api", tags=["storefront"])


def product_json(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "brand": p.brand,
        "description": p.description,
        "price": p.price,
        "currency": p.currency,
        "in_stock": p.in_stock,
        "stock_quantity": p.stock_quantity,
        "image_url": p.image_url,
        "is_test_data": p.is_test_data,
        "specs": [
            {"key": s.key, "value_text": s.value_text, "value_num": s.value_num, "unit": s.unit}
            for s in p.specs
        ],
    }


@router.get("/products")
def products(
    db: Annotated[Session, Depends(get_db)],
    q: str | None = None,
    category: str | None = None,
    brand: str | None = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
    available: bool | None = None,
    sort: Literal["name", "price_asc", "price_desc"] = "name",
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=60),
):
    stmt = select(Product).options(selectinload(Product.specs))
    count_stmt = select(func.count(Product.id))
    clauses = []
    if q:
        clauses.append(
            or_(
                Product.name.icontains(q, autoescape=True),
                Product.brand.icontains(q, autoescape=True),
                Product.description.icontains(q, autoescape=True),
            )
        )
    if category:
        clauses.append(func.lower(Product.category) == category.lower())
    if brand:
        clauses.append(func.lower(Product.brand) == brand.lower())
    if min_price is not None:
        clauses.append(Product.price >= min_price)
    if max_price is not None:
        clauses.append(Product.price <= max_price)
    if available is not None:
        clauses.append(Product.in_stock.is_(available))
    stmt, count_stmt = stmt.where(*clauses), count_stmt.where(*clauses)
    ordering = {
        "name": func.lower(Product.name).asc(),
        "price_asc": Product.price.asc().nullslast(),
        "price_desc": Product.price.desc().nullslast(),
    }[sort]
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(ordering, Product.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [product_json(p) for p in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/products/{product_id}")
def product_detail(product_id: int, db: Annotated[Session, Depends(get_db)]):
    product = db.scalar(
        select(Product).where(Product.id == product_id).options(selectinload(Product.specs))
    )
    if not product:
        raise HTTPException(404, "Product not found")
    result = product_json(product)
    related = db.scalars(
        select(Product)
        .where(Product.category == product.category, Product.id != product.id)
        .options(selectinload(Product.specs))
        .limit(4)
    ).all()
    result["related"] = [product_json(p) for p in related]
    return result


@router.get("/categories")
def categories(db: Annotated[Session, Depends(get_db)]):
    return [
        {"name": name, "count": count}
        for name, count in db.execute(
            select(Product.category, func.count(Product.id))
            .group_by(Product.category)
            .order_by(Product.category)
        )
    ]


@router.get("/promotions")
def promotions(db: Annotated[Session, Depends(get_db)]):
    today = date.today()
    rows = db.scalars(
        select(Promotion)
        .where(
            or_(Promotion.starts_at.is_(None), Promotion.starts_at <= today),
            or_(Promotion.ends_at.is_(None), Promotion.ends_at >= today),
        )
        .order_by(Promotion.id)
    ).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "conditions": p.conditions,
            "product_id": p.product_id,
            "category": p.category,
            "is_test_data": p.is_test_data,
        }
        for p in rows
    ]


class CartChange(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=99)


class QuantityChange(BaseModel):
    quantity: int = Field(ge=1, le=99)


def _cart(db: Session, user_id: int, create: bool = True) -> Cart | None:
    cart = db.scalar(
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
    )
    if not cart and create:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.flush()
    return cart


def cart_json(cart: Cart | None) -> dict:
    items = (
        []
        if not cart
        else [
            {
                "id": i.id,
                "quantity": i.quantity,
                "subtotal": i.product.price * i.quantity if i.product.price is not None else None,
                "product": product_json(i.product),
            }
            for i in cart.items
        ]
    )
    return {
        "items": items,
        "item_count": sum(i["quantity"] for i in items),
        "total": sum((i["subtotal"] or Decimal(0)) for i in items),
        "currency": "DZD",
    }


@router.get("/cart")
def get_cart(user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)]):
    return cart_json(_cart(db, user.id, False))


@router.post("/cart/items", status_code=201)
def add_cart(
    body: CartChange,
    session: Annotated[UserSession, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db)],
):
    p = db.get(Product, body.product_id)
    if not p or p.in_stock is not True or p.price is None:
        raise HTTPException(409, "Product is not available for purchase")
    cart = _cart(db, session.user_id)
    item = next((i for i in cart.items if i.product_id == p.id), None)
    quantity = body.quantity + (item.quantity if item else 0)
    if p.stock_quantity is None or quantity > p.stock_quantity:
        raise HTTPException(409, "Requested quantity is unavailable")
    if item:
        item.quantity = quantity
    else:
        cart.items.append(CartItem(product_id=p.id, quantity=quantity))
    db.commit()
    return cart_json(_cart(db, session.user_id))


@router.patch("/cart/items/{item_id}")
def update_cart(
    item_id: int,
    body: QuantityChange,
    session: Annotated[UserSession, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db)],
):
    cart = _cart(db, session.user_id, False)
    item = next((i for i in (cart.items if cart else []) if i.id == item_id), None)
    if not item:
        raise HTTPException(404, "Cart item not found")
    if item.product.stock_quantity is None or body.quantity > item.product.stock_quantity:
        raise HTTPException(409, "Requested quantity is unavailable")
    item.quantity = body.quantity
    db.commit()
    return cart_json(_cart(db, session.user_id))


@router.delete("/cart/items/{item_id}")
def delete_cart(
    item_id: int,
    session: Annotated[UserSession, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db)],
):
    cart = _cart(db, session.user_id, False)
    item = next((i for i in (cart.items if cart else []) if i.id == item_id), None)
    if not item:
        raise HTTPException(404, "Cart item not found")
    db.delete(item)
    db.commit()
    return cart_json(_cart(db, session.user_id))


class CheckoutRequest(BaseModel):
    customer_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(pattern=r"^[0-9+ ()-]{8,30}$")
    wilaya: str = Field(min_length=2, max_length=100)
    delivery_address: str = Field(min_length=8, max_length=500)


def order_json(o: Order) -> dict:
    return {
        "id": o.id,
        "customer_name": o.customer_name,
        "phone": o.phone,
        "wilaya": o.wilaya,
        "delivery_address": o.delivery_address,
        "total": o.total,
        "currency": o.currency,
        "status": o.status,
        "is_demo": o.is_demo,
        "created_at": o.created_at,
        "items": [
            {
                "product_id": i.product_id,
                "product_name": i.product_name,
                "unit_price": i.unit_price,
                "quantity": i.quantity,
            }
            for i in o.items
        ],
    }


@router.post("/orders/demo", status_code=201)
def checkout(
    body: CheckoutRequest,
    session: Annotated[UserSession, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db)],
):
    cart = _cart(db, session.user_id, False)
    if not cart or not cart.items:
        raise HTTPException(409, "Cart is empty")
    product_ids = [i.product_id for i in cart.items]
    locked = {
        p.id: p
        for p in db.scalars(
            select(Product).where(Product.id.in_(product_ids)).with_for_update()
        ).all()
    }
    total = Decimal(0)
    order_items = []
    for item in cart.items:
        p = locked[item.product_id]
        if (
            p.price is None
            or p.in_stock is not True
            or p.stock_quantity is None
            or item.quantity > p.stock_quantity
        ):
            raise HTTPException(409, f"{p.name} is no longer available in that quantity")
        total += p.price * item.quantity
        order_items.append(
            OrderItem(
                product_id=p.id, product_name=p.name, unit_price=p.price, quantity=item.quantity
            )
        )
        p.stock_quantity -= item.quantity
        if p.stock_quantity == 0:
            p.in_stock = False
    order = Order(
        user_id=session.user_id,
        customer_name=body.customer_name.strip(),
        phone=body.phone.strip(),
        wilaya=body.wilaya.strip(),
        delivery_address=body.delivery_address.strip(),
        total=total,
        currency="DZD",
        status="demo_confirmed",
        is_demo=True,
        created_at=datetime.now(UTC),
        items=order_items,
    )
    db.add(order)
    for item in list(cart.items):
        db.delete(item)
    db.commit()
    db.refresh(order)
    return order_json(order)


@router.get("/orders/me")
def my_orders(
    user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)]
):
    return [
        order_json(o)
        for o in db.scalars(
            select(Order)
            .where(Order.user_id == user.id)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
        ).all()
    ]


@router.get("/orders/{order_id}")
def order_detail(
    order_id: int,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user.id)
        .options(selectinload(Order.items))
    )
    if not order:
        raise HTTPException(404, "Order not found")
    return order_json(order)
