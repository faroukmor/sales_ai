from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Product
from app.main import app


def client_for(db_session: Session) -> TestClient:
    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def register(client: TestClient, email: str = "buyer@example.com") -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Demo Buyer",
            "email": email,
            "password": "SecurePass123",
            "confirm_password": "SecurePass123",
        },
    )
    assert response.status_code == 201
    return response.json()["csrf_token"]


def test_registration_login_logout_and_duplicate(db_session: Session) -> None:
    client = client_for(db_session)
    csrf = register(client)
    assert client.get("/api/auth/me").status_code == 200
    assert client.post(
        "/api/auth/register",
        json={
            "full_name": "Duplicate",
            "email": "BUYER@example.com",
            "password": "SecurePass123",
            "confirm_password": "SecurePass123",
        },
    ).status_code == 409
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert client.post(
        "/api/auth/login", json={"email": "buyer@example.com", "password": "wrong"}
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": "buyer@example.com", "password": "SecurePass123"},
    ).status_code == 200
    app.dependency_overrides.clear()


def test_catalog_cart_checkout_and_ownership(db_session: Session) -> None:
    product = Product(
        name="DEMO-CART-01",
        category="Informatique",
        brand="Demo",
        price=Decimal("1000"),
        currency="DZD",
        in_stock=True,
        stock_quantity=3,
        is_test_data=True,
    )
    db_session.add(product)
    db_session.commit()
    client = client_for(db_session)
    csrf = register(client)
    listing = client.get("/api/products", params={"category": "Informatique"})
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    added = client.post(
        "/api/cart/items",
        headers={"X-CSRF-Token": csrf},
        json={"product_id": product.id, "quantity": 2},
    )
    assert added.status_code == 201
    assert Decimal(str(added.json()["total"])) == Decimal("2000")
    order = client.post(
        "/api/orders/demo",
        headers={"X-CSRF-Token": csrf},
        json={
            "customer_name": "Demo Buyer",
            "phone": "0550000000",
            "wilaya": "Alger",
            "delivery_address": "Demo address only",
        },
    )
    assert order.status_code == 201
    assert order.json()["is_demo"] is True
    assert Decimal(str(order.json()["items"][0]["unit_price"])) == Decimal("1000")
    assert client.get("/api/cart").json()["items"] == []
    assert len(client.get("/api/orders/me").json()) == 1

    other = TestClient(app)
    register(other, "other@example.com")
    assert other.get(f"/api/orders/{order.json()['id']}").status_code == 404
    app.dependency_overrides.clear()
