"""Admin product management: specifications, catalog schema, permissions and store groups."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.routes.admin import router as admin_router
from app.api.routes.storefront import router as storefront_router
from app.core.catalog_schema import PRODUCT_TYPES, TYPES_BY_KEY, spec_label, types_for_group
from app.core.config import get_settings
from app.db.database import get_db

ADMIN_EMAIL = "admin@example.com"


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ADMIN_EMAIL", ADMIN_EMAIL)
    get_settings.cache_clear()
    app = FastAPI()
    for router in (auth_router, admin_router, storefront_router):
        app.include_router(router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    get_settings.cache_clear()


def sign_up(client: TestClient, email: str) -> str:
    client.cookies.clear()
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Test User",
            "email": email,
            "password": "SecurePass123",
            "confirm_password": "SecurePass123",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["csrf_token"]


def payload(**overrides):
    base = {
        "name": "Samsung Galaxy Book",
        "category": "laptop",
        "brand": "Samsung",
        "price": 89900,
        "currency": "DZD",
        "stock_quantity": 5,
        "specs": [
            {"key": "ram_gb", "value_num": 16, "unit": "GB"},
            {"key": "storage_gb", "value_num": 512, "unit": "GB"},
            {"key": "processor", "value_text": "Intel Core i7"},
        ],
    }
    base.update(overrides)
    return base


def spec_map(product: dict) -> dict:
    return {s["key"]: s for s in product["specs"]}


def test_is_admin_flag_only_for_configured_email(client: TestClient) -> None:
    sign_up(client, "buyer@example.com")
    assert client.get("/api/auth/me").json()["user"]["is_admin"] is False
    sign_up(client, ADMIN_EMAIL.upper())  # email comparison is case-insensitive
    assert client.get("/api/auth/me").json()["user"]["is_admin"] is True


def test_non_admin_and_anonymous_cannot_use_admin_api(client: TestClient) -> None:
    assert client.get("/api/admin/catalog-schema").status_code == 401
    csrf = sign_up(client, "buyer@example.com")
    assert client.get("/api/admin/catalog-schema").status_code == 403
    response = client.post("/api/admin/products", json=payload(), headers={"X-CSRF-Token": csrf})
    assert response.status_code == 403


def test_catalog_schema_gives_fields_per_type(client: TestClient) -> None:
    sign_up(client, ADMIN_EMAIL)
    schema = client.get("/api/admin/catalog-schema").json()
    types = {t["key"]: t for g in schema["groups"] for t in g["types"]}
    assert len(types) == len(PRODUCT_TYPES)
    laptop = {f["key"]: f for f in types["laptop"]["fields"]}
    assert {"processor", "ram_gb", "storage_gb", "screen_inches", "warranty_months"} <= set(laptop)
    assert laptop["ram_gb"]["unit"] == "GB" and "16" in laptop["ram_gb"]["options"]
    assert types["laptop"]["assistant_supported"] is True
    assert types["washing_machine"]["assistant_supported"] is False
    assert "capacity_kg" in {f["key"] for f in types["washing_machine"]["fields"]}
    assert "built_in_receiver" in {f["key"] for f in types["tv"]["fields"]}


def test_assistant_spec_keys_keep_their_units() -> None:
    # The AI assistant filters on these keys with these units; the form must not diverge.
    fields = {f.key: f for t in PRODUCT_TYPES for f in t.fields}
    assert (fields["ram_gb"].unit, fields["storage_gb"].unit) == ("GB", "GB")
    assert (fields["screen_inches"].unit, fields["refresh_rate_hz"].unit) == ("inch", "Hz")
    for type_key in ("laptop", "tv", "smartphone"):
        assert type_key in TYPES_BY_KEY


def test_create_product_with_specs_shows_on_store_with_labels(client: TestClient) -> None:
    csrf = sign_up(client, ADMIN_EMAIL)
    response = client.post("/api/admin/products", json=payload(), headers={"X-CSRF-Token": csrf})
    assert response.status_code == 201, response.text
    created = response.json()
    assert spec_map(created)["ram_gb"]["unit"] == "GB"
    detail = client.get(f"/api/products/{created['id']}").json()
    specs = {s["key"]: s for s in detail["specs"]}
    assert specs["ram_gb"]["label"] == "RAM"
    assert specs["processor"]["value_text"] == "Intel Core i7"


def test_update_replaces_specs_including_re_adding_same_key(client: TestClient) -> None:
    csrf = sign_up(client, ADMIN_EMAIL)
    headers = {"X-CSRF-Token": csrf}
    product_id = client.post("/api/admin/products", json=payload(), headers=headers).json()["id"]
    response = client.patch(
        f"/api/admin/products/{product_id}",
        json={
            "specs": [
                {"key": "ram_gb", "value_num": 32, "unit": "GB"},  # changed
                {"key": "color", "value_text": "Silver"},  # added
            ]  # storage_gb and processor removed
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    specs = spec_map(response.json())
    assert set(specs) == {"ram_gb", "color"}
    assert float(specs["ram_gb"]["value_num"]) == 32
    # Omitting specs leaves them untouched
    response = client.patch(f"/api/admin/products/{product_id}", json={"price": 1}, headers=headers)
    assert set(spec_map(response.json())) == {"ram_gb", "color"}
    # Empty list removes all
    url = f"/api/admin/products/{product_id}"
    response = client.patch(url, json={"specs": []}, headers=headers)
    assert response.json()["specs"] == []


@pytest.mark.parametrize(
    "specs",
    [
        [{"key": "ram_gb", "value_num": 8}, {"key": "ram_gb", "value_num": 16}],  # duplicate key
        [{"key": "ram_gb"}],  # no value
        [{"key": "RAM GB", "value_num": 8}],  # invalid key
    ],
)
def test_invalid_specs_are_rejected(client: TestClient, specs) -> None:
    csrf = sign_up(client, ADMIN_EMAIL)
    response = client.post(
        "/api/admin/products", json=payload(specs=specs), headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,x", "ftp://x.test/a"])
def test_product_url_must_be_http(client: TestClient, url: str) -> None:
    csrf = sign_up(client, ADMIN_EMAIL)
    response = client.post(
        "/api/admin/products", json=payload(url=url), headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 422


def test_https_url_and_null_required_field(client: TestClient) -> None:
    csrf = sign_up(client, ADMIN_EMAIL)
    headers = {"X-CSRF-Token": csrf}
    created = client.post(
        "/api/admin/products", json=payload(url="https://example.com/p"), headers=headers
    )
    assert created.status_code == 201 and created.json()["url"] == "https://example.com/p"
    response = client.patch(
        f"/api/admin/products/{created.json()['id']}", json={"name": None}, headers=headers
    )
    assert response.status_code == 422  # used to be a 500 (NOT NULL violation)


def test_store_group_filters_by_product_types(client: TestClient) -> None:
    csrf = sign_up(client, ADMIN_EMAIL)
    headers = {"X-CSRF-Token": csrf}
    client.post("/api/admin/products", json=payload(), headers=headers)
    client.post(
        "/api/admin/products",
        json=payload(name="Washer 8kg", category="washing_machine", brand="LG", specs=[]),
        headers=headers,
    )
    laundry = client.get("/api/products", params={"category": "Lavage"}).json()
    assert [p["name"] for p in laundry["items"]] == ["Washer 8kg"]
    it = client.get("/api/products", params={"category": "informatique"}).json()
    assert [p["name"] for p in it["items"]] == ["Samsung Galaxy Book"]
    exact = client.get("/api/products", params={"category": "laptop"}).json()
    assert exact["total"] == 1
    labels = {c["name"]: c["label"] for c in client.get("/api/categories").json()}
    assert labels == {"laptop": "Laptop", "washing_machine": "Washing machine"}


def test_group_filter_matches_products_stored_under_the_group_name(client: TestClient) -> None:
    from app.db.models import Product

    session = next(client.app.dependency_overrides[get_db]())
    session.add(Product(name="Legacy", category="Informatique", currency="DZD", is_test_data=True))
    session.commit()
    result = client.get("/api/products", params={"category": "Informatique"}).json()
    assert [p["name"] for p in result["items"]] == ["Legacy"]


def test_schema_helpers() -> None:
    assert "washing_machine" in types_for_group("Lavage")
    assert spec_label("ram_gb") == "RAM"
    assert spec_label("bluetooth_version") == "Bluetooth version"
