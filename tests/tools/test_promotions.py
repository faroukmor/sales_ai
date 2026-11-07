from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from app.db.models import Product, Promotion
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_repository import PromotionRepository
from app.schemas.sales_functions import ToolStatus
from app.tools.promotions import PromotionsTool

TODAY = date(2026, 6, 15)


@pytest.fixture
def promotion_data(db_session: Session):
    laptop = Product(name="Laptop", category="laptop", brand="Brand")
    tv = Product(name="TV", category="tv", brand="Brand")
    db_session.add_all([laptop, tv])
    db_session.flush()
    db_session.add_all(
        [
            Promotion(
                title="Global active",
                description="Global",
                conditions="One per order",
                source="test",
                starts_at=TODAY,
                ends_at=TODAY,
            ),
            Promotion(
                title="Laptop category",
                description="Laptop",
                conditions="Eligible laptops",
                source="test",
                category="laptop",
                starts_at=TODAY - timedelta(days=1),
                ends_at=TODAY + timedelta(days=1),
            ),
            Promotion(
                title="TV product",
                description="TV",
                conditions="This TV only",
                source="test",
                product_id=tv.id,
                starts_at=TODAY,
                ends_at=TODAY + timedelta(days=1),
            ),
            Promotion(
                title="Expired",
                source="test",
                category="laptop",
                starts_at=TODAY - timedelta(days=2),
                ends_at=TODAY - timedelta(days=1),
            ),
            Promotion(
                title="Future",
                source="test",
                category="laptop",
                starts_at=TODAY + timedelta(days=1),
                ends_at=TODAY + timedelta(days=2),
            ),
            Promotion(title="Unknown dates", source="test", category="laptop"),
        ]
    )
    db_session.commit()
    repository = PromotionRepository(db_session, date_provider=lambda: TODAY)
    tool = PromotionsTool(repository, ProductRepository(db_session))
    return tool, laptop, tv


def test_active_boundaries_and_global_offer(promotion_data) -> None:
    tool, _, _ = promotion_data
    result = tool.lookup()
    assert {item.title for item in result.promotions} == {
        "Global active",
        "Laptop category",
        "TV product",
    }


def test_expired_future_and_unknown_dates_are_excluded(promotion_data) -> None:
    tool, _, _ = promotion_data
    titles = {item.title for item in tool.lookup(category="laptop").promotions}
    assert "Expired" not in titles
    assert "Future" not in titles
    assert "Unknown dates" not in titles


def test_product_and_category_eligibility(promotion_data) -> None:
    tool, laptop, tv = promotion_data
    laptop_titles = {item.title for item in tool.lookup(product_ids=[laptop.id]).promotions}
    tv_titles = {item.title for item in tool.lookup(product_ids=[tv.id]).promotions}
    assert laptop_titles == {"Global active", "Laptop category"}
    assert tv_titles == {"Global active", "TV product"}


def test_invalid_product_is_controlled(promotion_data) -> None:
    tool, _, _ = promotion_data
    result = tool.lookup(product_ids=[9999])
    assert result.status is ToolStatus.NOT_FOUND
    assert result.promotions == []


def test_incomplete_active_promotion_is_reported(promotion_data, db_session: Session) -> None:
    tool, _, _ = promotion_data
    incomplete = Promotion(
        title="Incomplete active",
        source="test",
        starts_at=TODAY,
        ends_at=TODAY,
    )
    db_session.add(incomplete)
    db_session.commit()
    result = tool.lookup()
    assert incomplete.id in result.incomplete_promotion_ids
