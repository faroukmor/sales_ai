from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Promotion


def test_invalid_promotion_interval_is_rejected(db_session: Session) -> None:
    db_session.add(
        Promotion(
            title="Invalid",
            source="unit test",
            starts_at=date(2026, 2, 2),
            ends_at=date(2026, 2, 1),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unknown_promotion_boundaries_are_preserved(db_session: Session) -> None:
    promotion = Promotion(title="Unknown dates", source="unit test")
    db_session.add(promotion)
    db_session.commit()

    assert promotion.starts_at is None
    assert promotion.ends_at is None
