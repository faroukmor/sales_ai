from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.db.models import Product
from app.db.seed import seed_database
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_repository import PromotionRepository
from app.schemas.sales_functions import ToolStatus
from app.tools.product_comparison import ProductComparisonTool

TODAY = date(2026, 6, 15)


@pytest.fixture
def comparison(db_session: Session) -> tuple[ProductComparisonTool, ProductRepository]:
    seed_database(db_session, date_provider=lambda: TODAY)
    products = ProductRepository(db_session)
    promotions = PromotionRepository(db_session, date_provider=lambda: TODAY)
    return ProductComparisonTool(products, promotions), products


def test_compares_two_products_with_database_values(comparison) -> None:
    tool, repository = comparison
    first = repository.find_by_name("TEST-LAPTOP-01")[0]
    second = repository.find_by_name("TEST-LAPTOP-02")[0]
    result = tool.compare(product_ids=[first.id, second.id])

    assert result.status is ToolStatus.SUCCESS
    ram = next(row for row in result.rows if row.attribute == "ram_gb")
    assert [cell.value for cell in ram.values] == ["16 GB", "8 GB"]
    assert not hasattr(result, "winner")


def test_missing_product_is_not_substituted(comparison) -> None:
    tool, repository = comparison
    existing = repository.find_by_name("TEST-LAPTOP-01")[0]
    result = tool.compare(product_ids=[existing.id, 99999])
    assert result.status is ToolStatus.NOT_FOUND
    assert result.unresolved_references == ["99999"]
    assert [product.id for product in result.products] == [existing.id]


def test_ambiguous_reference_is_explicit(comparison, db_session: Session) -> None:
    tool, _ = comparison
    db_session.add(Product(name="TEST-LAPTOP-01", category="laptop"))
    db_session.commit()
    result = tool.compare(references=["TEST-LAPTOP-01", "TEST-LAPTOP-02"])
    assert result.status is ToolStatus.AMBIGUOUS
    assert len(result.ambiguous_references["TEST-LAPTOP-01"]) == 2


def test_unknown_specs_are_na_and_reported(comparison) -> None:
    tool, _ = comparison
    result = tool.compare(references=["TEST-LAPTOP-01", "TEST-LAPTOP-04"])
    processor = next(row for row in result.rows if row.attribute == "processor")
    assert processor.values[1].value == "N/A"
    assert any(item.endswith(":processor") for item in result.missing_information)


def test_identical_product_ids_do_not_form_comparison(comparison) -> None:
    tool, repository = comparison
    product = repository.find_by_name("TEST-LAPTOP-01")[0]
    result = tool.compare(product_ids=[product.id, product.id])
    assert result.status is ToolStatus.NOT_FOUND


def test_follow_up_uses_last_product_ids(comparison) -> None:
    tool, repository = comparison
    ids = [
        repository.find_by_name("TEST-TV-01")[0].id,
        repository.find_by_name("TEST-TV-02")[0].id,
    ]
    result = tool.compare(last_product_ids=ids)
    assert result.status is ToolStatus.SUCCESS
    assert [product.id for product in result.products] == ids
