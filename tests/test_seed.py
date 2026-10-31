from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Product, Promotion
from app.db.seed import seed_database


def test_seed_is_idempotent(db_session: Session) -> None:
    def fixed_today() -> date:
        return date(2026, 6, 15)

    first = seed_database(db_session, fixed_today)
    second = seed_database(db_session, fixed_today)

    assert first.products_created == 12
    assert first.promotions_created == 4
    assert second.products_skipped == 12
    assert second.promotions_skipped == 4
    assert db_session.scalar(select(func.count()).select_from(Product)) == 12
    assert db_session.scalar(select(func.count()).select_from(Promotion)) == 4


def test_seed_refuses_to_modify_non_test_collision(db_session: Session) -> None:
    db_session.add(Product(name="TEST-LAPTOP-01", category="real", is_test_data=False))
    db_session.commit()

    with pytest.raises(ValueError, match="non-test product"):
        seed_database(db_session, lambda: date(2026, 6, 15))

    product = db_session.scalar(select(Product).where(Product.name == "TEST-LAPTOP-01"))
    assert product is not None
    assert product.category == "real"
