from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Product
from app.db.seed import seed_database
from app.repositories.product_repository import ProductRepository
from app.schemas.product_filters import ProductFilters, SpecConstraint


@pytest.fixture
def repository(db_session: Session) -> ProductRepository:
    seed_database(db_session, date_provider=lambda: date(2026, 6, 15))
    return ProductRepository(db_session)


def test_price_category_and_deterministic_sort(repository: ProductRepository) -> None:
    results = repository.search(ProductFilters(category="laptop", max_price=100000))
    assert [product.name for product in results] == ["TEST-LAPTOP-02", "TEST-LAPTOP-01"]
    assert all(product.price is not None for product in results)


def test_brand_and_stock_filters(repository: ProductRepository) -> None:
    branded = repository.search(ProductFilters(brand="Lumina"))
    available_tvs = repository.search(ProductFilters(category="tv", in_stock_only=True))

    assert {product.name for product in branded} == {"TEST-TV-01", "TEST-TV-02"}
    assert [product.name for product in available_tvs] == ["TEST-TV-01", "TEST-TV-03"]


def test_numeric_and_multiple_spec_constraints(repository: ProductRepository) -> None:
    results = repository.search(
        ProductFilters(
            category="laptop",
            max_price=Decimal("100000"),
            spec_constraints=[
                SpecConstraint(key="ram_gb", operator="gte", value=16),
                SpecConstraint(key="storage_gb", operator="gte", value=512),
                SpecConstraint(key="screen_inches", operator="gte", value=15),
            ],
        )
    )
    assert [product.name for product in results] == ["TEST-LAPTOP-01"]


def test_exact_name_precedes_partial_and_ambiguity_is_explicit(
    repository: ProductRepository, db_session: Session
) -> None:
    db_session.add(Product(name="TEST-LAPTOP-01", category="laptop"))
    db_session.commit()

    exact = repository.find_by_name("test-laptop-01")
    partial = repository.find_by_name("LAPTOP-0", limit=10)

    assert len(exact) == 2
    assert all(product.name == "TEST-LAPTOP-01" for product in exact)
    assert len(partial) >= 4


def test_empty_and_wildcard_input_are_safe(
    repository: ProductRepository, db_session: Session
) -> None:
    assert repository.find_by_name("does-not-exist") == []
    assert repository.find_by_name("%_' OR 1=1 --") == []
    assert db_session.scalar(select(func.count()).select_from(Product)) == 12


def test_lists_lookup_specs_and_limit_validation(repository: ProductRepository) -> None:
    product = repository.find_by_name("TEST-TV-01")[0]
    assert repository.get_by_id(product.id) is product
    assert "tv" in repository.list_categories()
    assert "Lumina" in repository.list_brands()
    assert {spec.key for spec in repository.get_product_specs(product.id)} >= {
        "screen_inches",
        "resolution",
    }
    with pytest.raises(ValueError):
        repository.search(ProductFilters(), limit=0)
