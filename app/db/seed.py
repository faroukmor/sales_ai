from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Product, ProductSpec, Promotion


@dataclass(frozen=True)
class SeedReport:
    products_created: int = 0
    products_updated: int = 0
    products_skipped: int = 0
    promotions_created: int = 0
    promotions_updated: int = 0
    promotions_skipped: int = 0


PRODUCTS: tuple[dict[str, Any], ...] = (
    {
        "name": "TEST-LAPTOP-01",
        "category": "laptop",
        "brand": "Northstar",
        "price": Decimal("95000.00"),
        "in_stock": True,
        "specs": {
            "ram_gb": (16, "GB"),
            "storage_gb": (512, "GB"),
            "processor": "Orion i7",
            "screen_inches": (Decimal("15.6"), "inch"),
        },
    },
    {
        "name": "TEST-LAPTOP-02",
        "category": "laptop",
        "brand": "Northstar",
        "price": Decimal("60000.00"),
        "in_stock": True,
        "specs": {
            "ram_gb": (8, "GB"),
            "storage_gb": (256, "GB"),
            "processor": "Orion i5",
            "screen_inches": (14, "inch"),
        },
    },
    {
        "name": "TEST-LAPTOP-03",
        "category": "laptop",
        "brand": "Atlas Computing",
        "price": Decimal("135000.00"),
        "in_stock": False,
        "specs": {
            "ram_gb": (32, "GB"),
            "storage_gb": (1000, "GB"),
            "processor": "Zenith Pro",
            "screen_inches": (16, "inch"),
        },
    },
    {
        "name": "TEST-LAPTOP-04",
        "category": "laptop",
        "brand": None,
        "price": None,
        "in_stock": None,
        "specs": {"ram_gb": (16, "GB"), "storage_gb": (512, "GB")},
    },
    {
        "name": "TEST-TV-01",
        "category": "tv",
        "brand": "Lumina",
        "price": Decimal("78000.00"),
        "in_stock": True,
        "specs": {
            "screen_inches": (55, "inch"),
            "resolution": "4K",
            "display_type": "QLED",
            "refresh_rate_hz": (120, "Hz"),
        },
    },
    {
        "name": "TEST-TV-02",
        "category": "tv",
        "brand": "Lumina",
        "price": Decimal("46000.00"),
        "in_stock": False,
        "specs": {
            "screen_inches": (43, "inch"),
            "resolution": "4K",
            "display_type": "LED",
            "refresh_rate_hz": (60, "Hz"),
        },
    },
    {
        "name": "TEST-TV-03",
        "category": "tv",
        "brand": "Sahara Vision",
        "price": None,
        "in_stock": True,
        "specs": {
            "screen_inches": (65, "inch"),
            "resolution": "4K",
            "display_type": "OLED",
            "refresh_rate_hz": (120, "Hz"),
        },
    },
    {
        "name": "TEST-TV-04",
        "category": "tv",
        "brand": "Sahara Vision",
        "price": Decimal("32000.00"),
        "in_stock": None,
        "specs": {"screen_inches": (32, "inch"), "resolution": "Full HD", "display_type": "LED"},
    },
    {
        "name": "TEST-PHONE-01",
        "category": "smartphone",
        "brand": "Dune Mobile",
        "price": Decimal("42000.00"),
        "in_stock": True,
        "specs": {
            "ram_gb": (8, "GB"),
            "storage_gb": (128, "GB"),
            "screen_inches": (Decimal("6.5"), "inch"),
        },
    },
    {
        "name": "TEST-PHONE-02",
        "category": "smartphone",
        "brand": "Dune Mobile",
        "price": Decimal("68000.00"),
        "in_stock": True,
        "specs": {
            "ram_gb": (12, "GB"),
            "storage_gb": (256, "GB"),
            "screen_inches": (Decimal("6.7"), "inch"),
        },
    },
    {
        "name": "TEST-PHONE-03",
        "category": "smartphone",
        "brand": "Aurora Labs",
        "price": Decimal("89000.00"),
        "in_stock": False,
        "specs": {
            "ram_gb": (12, "GB"),
            "storage_gb": (512, "GB"),
            "screen_inches": (Decimal("6.8"), "inch"),
        },
    },
    {
        "name": "TEST-PHONE-04",
        "category": "smartphone",
        "brand": "Aurora Labs",
        "price": None,
        "in_stock": None,
        "specs": {"ram_gb": (6, "GB"), "storage_gb": (128, "GB")},
    },
)

# Original, clearly fictional storefront inventory. Specifications are illustrative demo data.
_STORE_CATEGORIES = (
    ("washing-machine", "Lavage", ("AquaWash", "Sirocco"), 62000),
    ("refrigerator", "Froid", ("NordCool", "Atlas Home"), 78000),
    ("air-conditioner", "Climatisation", ("Breeze", "Sahara Air"), 69000),
    ("television", "Multimédia", ("Lumina", "Vista"), 52000),
    ("cooking", "Cuisson", ("Chefline", "Flamme"), 34000),
    ("heating", "Chauffage", ("Therma", "Warmia"), 18000),
    ("small-appliance", "Petit électroménager", ("KitchenJoy", "DailyMix"), 7500),
    ("laptop", "Informatique", ("Northstar", "Atlas Computing"), 89000),
)

STOREFRONT_PRODUCTS: tuple[dict[str, Any], ...] = tuple(
    {
        "name": f"DEMO-{slug.upper()}-{number:02d}",
        "category": label,
        "brand": brands[number % 2],
        "price": Decimal(base + number * (base // 12)),
        "in_stock": number != 5,
        "stock_quantity": 0 if number == 5 else 4 + number * 2,
        "description": (
            f"Produit de démonstration {label.lower()}; caractéristiques et prix "
            "illustratifs uniquement."
        ),
        "image_url": None,
        "specs": {
            "demo_reference": f"{slug[:3].upper()}-{number:03d}",
            "data_notice": "Illustrative demo specification",
        },
    }
    for slug, label, brands, base in _STORE_CATEGORIES
    for number in range(1, 7)
)


def seed_database(
    session: Session,
    date_provider: Callable[[], date] = date.today,
) -> SeedReport:
    counters = {
        "products_created": 0,
        "products_updated": 0,
        "products_skipped": 0,
        "promotions_created": 0,
        "promotions_updated": 0,
        "promotions_skipped": 0,
    }
    names = [item["name"] for item in PRODUCTS]

    with session.begin():
        existing_products = {
            product.name: product
            for product in session.scalars(select(Product).where(Product.name.in_(names)))
        }
        seeded_products: dict[str, Product] = {}
        for item in PRODUCTS:
            product, outcome = _seed_product(session, existing_products.get(item["name"]), item)
            counters[f"products_{outcome}"] += 1
            seeded_products[product.name] = product

        session.flush()
        today = date_provider()
        promotion_data = (
            {
                "title": "TEST-PROMO-01",
                "description": "Fictional active laptop catalog promotion.",
                "conditions": "Test data only.",
                "starts_at": today - timedelta(days=7),
                "ends_at": today + timedelta(days=7),
                "product_id": None,
                "category": "laptop",
            },
            {
                "title": "TEST-PROMO-02",
                "description": "Fictional expired product promotion.",
                "conditions": "Test data only.",
                "starts_at": today - timedelta(days=30),
                "ends_at": today - timedelta(days=1),
                "product_id": seeded_products["TEST-TV-01"].id,
                "category": None,
            },
            {
                "title": "TEST-PROMO-03",
                "description": "Fictional future smartphone promotion.",
                "conditions": "Test data only.",
                "starts_at": today + timedelta(days=7),
                "ends_at": today + timedelta(days=21),
                "product_id": None,
                "category": "smartphone",
            },
            {
                "title": "TEST-PROMO-04",
                "description": "Fictional promotion with unknown validity.",
                "conditions": "Test data only.",
                "starts_at": None,
                "ends_at": None,
                "product_id": seeded_products["TEST-PHONE-01"].id,
                "category": None,
            },
        )
        titles = [item["title"] for item in promotion_data]
        existing_promotions = {
            promotion.title: promotion
            for promotion in session.scalars(select(Promotion).where(Promotion.title.in_(titles)))
        }
        for item in promotion_data:
            outcome = _seed_promotion(session, existing_promotions.get(item["title"]), item)
            counters[f"promotions_{outcome}"] += 1

    return SeedReport(**counters)


def seed_storefront(session: Session) -> SeedReport:
    counters = {name: 0 for name in SeedReport.__dataclass_fields__}
    names = [item["name"] for item in STOREFRONT_PRODUCTS]
    with session.begin():
        existing = {
            p.name: p for p in session.scalars(select(Product).where(Product.name.in_(names)))
        }
        for item in STOREFRONT_PRODUCTS:
            _product, outcome = _seed_product(session, existing.get(item["name"]), item)
            counters[f"products_{outcome}"] += 1
    return SeedReport(**counters)


def _seed_product(
    session: Session,
    product: Product | None,
    item: dict[str, Any],
) -> tuple[Product, str]:
    if product is not None and not product.is_test_data:
        raise ValueError(f"seed identifier conflicts with non-test product: {item['name']}")

    created = product is None
    if product is None:
        product = Product(name=item["name"], category=item["category"], is_test_data=True)
        session.add(product)

    changed = created
    for field in ("category", "brand", "price", "in_stock", "stock_quantity", "image_url"):
        if field not in item:
            continue
        if getattr(product, field) != item[field]:
            setattr(product, field, item[field])
            changed = True
    defaults = {
        "description": item.get(
            "description", "Fictional product created solely for Sales AI development tests."
        ),
        "currency": "DZD",
        "url": None,
        "is_test_data": True,
    }
    for field, value in defaults.items():
        if getattr(product, field) != value:
            setattr(product, field, value)
            changed = True

    existing_specs = {spec.key: spec for spec in product.specs}
    for key, raw_value in item["specs"].items():
        value, unit = raw_value if isinstance(raw_value, tuple) else (raw_value, None)
        value_num = Decimal(str(value)) if not isinstance(value, str) else None
        value_text = value if isinstance(value, str) else None
        spec = existing_specs.get(key)
        if spec is None:
            product.specs.append(
                ProductSpec(key=key, value_num=value_num, value_text=value_text, unit=unit)
            )
            changed = True
        elif (spec.value_num, spec.value_text, spec.unit) != (value_num, value_text, unit):
            spec.value_num, spec.value_text, spec.unit = value_num, value_text, unit
            changed = True

    return product, "created" if created else "updated" if changed else "skipped"


def _seed_promotion(
    session: Session,
    promotion: Promotion | None,
    item: dict[str, Any],
) -> str:
    if promotion is not None and not promotion.is_test_data:
        raise ValueError(f"seed identifier conflicts with non-test promotion: {item['title']}")
    created = promotion is None
    if promotion is None:
        promotion = Promotion(title=item["title"], source="Sales AI fictional seed data")
        session.add(promotion)

    changed = created
    values = {
        **item,
        "source": "Sales AI fictional seed data",
        "is_test_data": True,
    }
    for field, value in values.items():
        if getattr(promotion, field) != value:
            setattr(promotion, field, value)
            changed = True
    return "created" if created else "updated" if changed else "skipped"


def main() -> None:
    with SessionLocal() as session:
        report = seed_database(session)
        storefront_report = seed_storefront(session)
    print(
        "Seed complete: "
        f"products(created={report.products_created}, updated={report.products_updated}, "
        f"skipped={report.products_skipped}); "
        f"promotions(created={report.promotions_created}, "
        f"updated={report.promotions_updated}, skipped={report.promotions_skipped})"
    )
    print(
        "Storefront seed complete: "
        f"products(created={storefront_report.products_created}, "
        f"updated={storefront_report.products_updated}, "
        f"skipped={storefront_report.products_skipped})"
    )


if __name__ == "__main__":
    main()
