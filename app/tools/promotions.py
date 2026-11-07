"""Active and eligible promotion lookup."""

from __future__ import annotations

from collections.abc import Iterable

from app.db.models import Product, Promotion
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_repository import PromotionRepository
from app.schemas.promotion import PromotionRead
from app.schemas.query_plan import QueryPlan
from app.schemas.sales_functions import PromotionLookupResult, ToolStatus


class PromotionsTool:
    """Return only date-valid promotions eligible for the requested catalog scope.

    Promotion validity uses the repository's injected calendar date. Production defaults
    to the current UTC date, while tests can inject a fixed date.
    """

    def __init__(
        self,
        promotion_repository: PromotionRepository,
        product_repository: ProductRepository,
    ) -> None:
        self._promotions = promotion_repository
        self._products = product_repository

    def lookup(
        self,
        *,
        category: str | None = None,
        product_ids: Iterable[int] = (),
    ) -> PromotionLookupResult:
        ids = list(dict.fromkeys(product_ids))
        products: list[Product] = []
        missing_ids: list[int] = []
        for product_id in ids:
            product = self._products.get_by_id(product_id)
            if product is None:
                missing_ids.append(product_id)
            else:
                products.append(product)
        if missing_ids:
            return PromotionLookupResult(
                status=ToolStatus.NOT_FOUND,
                message=f"Unknown product identifiers: {missing_ids}",
            )

        categories = {product.category.lower() for product in products}
        lookup_category = category or (products[0].category if len(categories) == 1 else None)
        candidates = self._promotions.find_valid(lookup_category)
        eligible = [
            promotion
            for promotion in candidates
            if self._eligible(promotion, category, products)
        ]
        reads = [PromotionRead.model_validate(promotion) for promotion in eligible]
        incomplete = [
            promotion.id
            for promotion in eligible
            if not promotion.description or not promotion.conditions
        ]
        return PromotionLookupResult(
            status=ToolStatus.SUCCESS if reads else ToolStatus.NO_RESULTS,
            promotions=reads,
            incomplete_promotion_ids=incomplete,
        )

    def lookup_plan(self, plan: QueryPlan) -> PromotionLookupResult:
        products: list[Product] = []
        ambiguous: list[str] = []
        missing: list[str] = []
        for reference in plan.product_refs:
            matches = self._products.find_by_name(reference)
            if len(matches) > 1:
                ambiguous.append(reference)
            elif not matches:
                missing.append(reference)
            else:
                products.append(matches[0])
        if ambiguous:
            return PromotionLookupResult(
                status=ToolStatus.AMBIGUOUS,
                message=f"Ambiguous product references: {ambiguous}",
            )
        if missing:
            return PromotionLookupResult(
                status=ToolStatus.NOT_FOUND,
                message=f"Unknown product references: {missing}",
            )
        return self.lookup(category=plan.category, product_ids=[item.id for item in products])

    @staticmethod
    def _eligible(
        promotion: Promotion,
        category: str | None,
        products: list[Product],
    ) -> bool:
        product_ids = {product.id for product in products}
        categories = {product.category.lower() for product in products}
        if not products and category is None:
            return True
        if category is not None:
            categories.add(category.lower())
        if promotion.product_id is not None:
            if products:
                return promotion.product_id in product_ids
            return category is not None and promotion.product is not None and (
                promotion.product.category.lower() in categories
            )
        if promotion.category is not None:
            return not categories or promotion.category.lower() in categories
        return True
