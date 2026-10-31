from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.models import Product, Promotion
from app.repositories.promotion_repository import PromotionRepository

TODAY = date(2026, 6, 15)


def _promotion_data(db_session: Session) -> Product:
    product = Product(name="Target", category="laptop")
    product.promotions = [
        Promotion(title="Active product", source="test", starts_at=TODAY, ends_at=TODAY),
        Promotion(
            title="Expired",
            source="test",
            starts_at=TODAY - timedelta(days=2),
            ends_at=TODAY - timedelta(days=1),
        ),
        Promotion(
            title="Future",
            source="test",
            starts_at=TODAY + timedelta(days=1),
            ends_at=TODAY + timedelta(days=2),
        ),
        Promotion(title="Unknown", source="test"),
    ]
    db_session.add_all(
        [
            product,
            Promotion(
                title="Active category",
                source="test",
                category="laptop",
                starts_at=TODAY - timedelta(days=1),
                ends_at=TODAY + timedelta(days=1),
            ),
        ]
    )
    db_session.commit()
    return product


def test_validity_boundaries_and_exclusions(db_session: Session) -> None:
    _promotion_data(db_session)
    repository = PromotionRepository(db_session, date_provider=lambda: TODAY)

    assert {promotion.title for promotion in repository.find_valid()} == {
        "Active product",
        "Active category",
    }


def test_category_and_product_promotion_queries(db_session: Session) -> None:
    product = _promotion_data(db_session)
    repository = PromotionRepository(db_session, date_provider=lambda: TODAY)

    assert {promotion.title for promotion in repository.find_valid("LAPTOP")} == {
        "Active product",
        "Active category",
    }
    product_promotions = repository.find_by_product(product.id)
    assert {promotion.title for promotion in product_promotions} == {
        "Active product",
        "Expired",
        "Future",
        "Unknown",
    }
    assert repository.get_by_id(product_promotions[0].id) is not None
