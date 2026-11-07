from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Product
from app.db.seed import seed_database
from app.repositories.product_repository import ProductRepository
from app.schemas.product_filters import (
    ProductFilters,
    ProductSortBy,
    SortDirection,
    TextSpecConstraint,
)
from app.schemas.query_plan import QuerySpecificationConstraint
from app.schemas.sales_functions import ToolStatus
from app.tools.product_search import ProductSearchTool
from tests.intent_helpers import make_plan


@pytest.fixture
def tool(db_session: Session) -> ProductSearchTool:
    seed_database(db_session, date_provider=lambda: date(2026, 6, 15))
    return ProductSearchTool(ProductRepository(db_session))


def constraint(key: str, operator: str, value: str) -> QuerySpecificationConstraint:
    return QuerySpecificationConstraint(key=key, operator=operator, value=Decimal(value), unit="GB")


def test_budget_and_ram_are_hard_constraints(tool: ProductSearchTool) -> None:
    plan = make_plan(
        "laptop under 100000 DA with 16GB RAM",
        category="laptop",
        max_price=Decimal("100000"),
        currency="DZD",
        specification_constraints=[constraint("ram_gb", "gte", "16")],
    )
    result = tool.search(plan)

    assert result.status is ToolStatus.SUCCESS
    assert [product.name for product in result.products] == ["TEST-LAPTOP-01"]
    assert all(product.price is not None and product.price <= 100000 for product in result.products)


def test_brand_category_stock_and_multiple_filters(tool: ProductSearchTool) -> None:
    plan = make_plan(
        "available Northstar laptops",
        category="laptop",
        brand="Northstar",
        in_stock_only=True,
        specification_constraints=[constraint("storage_gb", "gte", "512")],
    )
    assert [item.name for item in tool.search(plan).products] == ["TEST-LAPTOP-01"]


def test_unknown_specification_is_controlled(tool: ProductSearchTool) -> None:
    plan = make_plan(
        "laptop with GPU",
        category="laptop",
        specification_constraints=[constraint("gpu_cores", "gte", "8")],
    )
    result = tool.search(plan)
    assert result.status is ToolStatus.INVALID_FILTERS
    assert result.unsupported_filters == ["gpu_cores"]


def test_empty_results_are_distinct(tool: ProductSearchTool) -> None:
    result = tool.search(make_plan("Acme laptops", category="laptop", brand="Acme"))
    assert result.status is ToolStatus.NO_RESULTS
    assert result.products == []


def test_injection_like_brand_is_parameterized(
    tool: ProductSearchTool, db_session: Session
) -> None:
    result = tool.search(make_plan("bad brand", brand="%' OR 1=1 --"))
    assert result.status is ToolStatus.NO_RESULTS
    assert db_session.scalar(select(func.count()).select_from(Product)) == 12


def test_exact_cpu_filter_and_configurable_sort(tool: ProductSearchTool) -> None:
    result = tool.search_filters(
        ProductFilters(
            category="laptop",
            text_spec_constraints=[TextSpecConstraint(key="processor", value="Orion i7")],
            sort_by=ProductSortBy.NAME,
            sort_direction=SortDirection.DESC,
        )
    )
    assert [product.name for product in result.products] == ["TEST-LAPTOP-01"]


def test_screen_size_filter(tool: ProductSearchTool) -> None:
    plan = make_plan(
        "large TV",
        category="tv",
        max_price=None,
        specification_constraints=[constraint("screen_inches", "gte", "55")],
    )
    assert {product.name for product in tool.search(plan).products} == {
        "TEST-TV-01",
        "TEST-TV-03",
    }
