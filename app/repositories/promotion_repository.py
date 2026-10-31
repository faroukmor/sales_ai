from collections.abc import Callable
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Product, Promotion


class PromotionRepository:
    def __init__(
        self,
        session: Session,
        date_provider: Callable[[], date] = date.today,
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
