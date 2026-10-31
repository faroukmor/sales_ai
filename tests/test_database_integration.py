import os
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.seed import seed_database
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_repository import PromotionRepository
from app.schemas.product_filters import ProductFilters, SpecConstraint

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def postgres_engine():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    database_name = make_url(database_url).database or ""
    if not database_name.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must target a database whose name ends with _test")

    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_postgresql_catalog_queries_and_constraints(postgres_engine) -> None:
    with Session(postgres_engine) as session:
        seed_database(session, lambda: date(2026, 6, 15))
        products = ProductRepository(session)
        promotions = PromotionRepository(session, lambda: date(2026, 6, 15))

        matches = products.search(
            ProductFilters(
                category="laptop",
                max_price=Decimal("100000"),
                spec_constraints=[SpecConstraint(key="ram_gb", operator="gte", value=16)],
            )
        )
        assert [product.name for product in matches] == ["TEST-LAPTOP-01"]
        assert [promotion.title for promotion in promotions.find_valid()] == ["TEST-PROMO-01"]
