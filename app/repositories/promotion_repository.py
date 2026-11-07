from collections.abc import Callable
from datetime import UTC, date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Product, Promotion


def utc_today() -> date:
    return datetime.now(UTC).date()


class PromotionRepository:
    def __init__(
        self,
        session: Session,
        date_provider: Callable[[], date] = utc_today,
    ) -> None:
        self._session = session
        self._date_provider = date_provider

    def find_valid(self, category: str | None = None) -> list[Promotion]:
        today = self._date_provider()
        statement = (
            select(Promotion)
            .outerjoin(Promotion.product)
            .where(
                Promotion.starts_at.is_not(None),
                Promotion.ends_at.is_not(None),
                Promotion.starts_at <= today,
                Promotion.ends_at >= today,
            )
            .options(selectinload(Promotion.product))
        )
        if category is not None:
            statement = statement.where(
                or_(
                    (Promotion.category.is_(None) & Promotion.product_id.is_(None)),
                    func.lower(Promotion.category) == category.lower(),
                    func.lower(Product.category) == category.lower(),
                )
            )
        statement = statement.order_by(Promotion.ends_at, Promotion.starts_at, Promotion.id)
        return list(self._session.scalars(statement).all())

    def find_by_product(self, product_id: int) -> list[Promotion]:
        if product_id < 1:
            return []
        statement = (
            select(Promotion)
            .where(Promotion.product_id == product_id)
            .options(selectinload(Promotion.product))
            .order_by(Promotion.starts_at.is_(None), Promotion.starts_at, Promotion.id)
        )
        return list(self._session.scalars(statement).all())

    def get_by_id(self, promotion_id: int) -> Promotion | None:
        if promotion_id < 1:
            return None
        statement = (
            select(Promotion)
            .where(Promotion.id == promotion_id)
            .options(selectinload(Promotion.product))
        )
        return self._session.scalar(statement)
