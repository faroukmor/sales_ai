from sqlalchemy import Select, exists, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Product, ProductSpec
from app.schemas.product_filters import ComparisonOperator, ProductFilters, SpecConstraint


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def search(self, filters: ProductFilters, limit: int = 10) -> list[Product]:
        self._validate_limit(limit)
        statement: Select[tuple[Product]] = select(Product).options(
            selectinload(Product.specs), selectinload(Product.promotions)
        )

        if filters.category is not None:
            statement = statement.where(func.lower(Product.category) == filters.category.lower())
        if filters.brand is not None:
            statement = statement.where(func.lower(Product.brand) == filters.brand.lower())
        if filters.min_price is not None:
            statement = statement.where(
                Product.price.is_not(None), Product.price >= filters.min_price
            )
        if filters.max_price is not None:
            statement = statement.where(
                Product.price.is_not(None), Product.price <= filters.max_price
            )
        if filters.in_stock_only:
            statement = statement.where(Product.in_stock.is_(True))

        for constraint in filters.spec_constraints:
            statement = statement.where(self._numeric_spec_exists(constraint))

        statement = statement.order_by(
            Product.price.is_(None), Product.price.asc(), Product.id.asc()
        ).limit(limit)
        return list(self._session.scalars(statement).all())

    def get_by_id(self, product_id: int) -> Product | None:
        if product_id < 1:
            return None
        statement = (
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.specs), selectinload(Product.promotions))
        )
        return self._session.scalar(statement)

    def find_by_name(self, name: str, limit: int = 5) -> list[Product]:
        self._validate_limit(limit)
        normalized = name.strip()
        if not normalized:
            return []

        base = select(Product).options(
            selectinload(Product.specs), selectinload(Product.promotions)
        )
        exact = (
            base.where(func.lower(Product.name) == normalized.lower())
            .order_by(Product.id)
            .limit(limit)
        )
        exact_matches = list(self._session.scalars(exact).all())
        if exact_matches:
            return exact_matches

        partial = (
            base.where(Product.name.icontains(normalized, autoescape=True))
            .order_by(func.length(Product.name), func.lower(Product.name), Product.id)
            .limit(limit)
        )
        return list(self._session.scalars(partial).all())

    def list_categories(self) -> list[str]:
        statement = (
            select(Product.category)
            .distinct()
            .order_by(func.lower(Product.category), Product.category)
        )
        return list(self._session.scalars(statement).all())

    def list_brands(self) -> list[str]:
        statement = (
            select(Product.brand)
            .where(Product.brand.is_not(None))
            .distinct()
            .order_by(func.lower(Product.brand), Product.brand)
        )
        return [brand for brand in self._session.scalars(statement) if brand is not None]

    def get_product_specs(self, product_id: int) -> list[ProductSpec]:
        if product_id < 1:
            return []
        statement = (
            select(ProductSpec)
            .where(ProductSpec.product_id == product_id)
            .order_by(ProductSpec.key, ProductSpec.id)
        )
        return list(self._session.scalars(statement).all())

    @staticmethod
    def _numeric_spec_exists(constraint: SpecConstraint):
        comparison = {
            ComparisonOperator.EQ: ProductSpec.value_num == constraint.value,
            ComparisonOperator.GTE: ProductSpec.value_num >= constraint.value,
            ComparisonOperator.LTE: ProductSpec.value_num <= constraint.value,
        }[constraint.operator]
        return exists(
            select(ProductSpec.id).where(
                ProductSpec.product_id == Product.id,
                ProductSpec.key == constraint.key,
                ProductSpec.value_num.is_not(None),
                comparison,
            )
        )

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
