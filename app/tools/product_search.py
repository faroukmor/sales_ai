"""Validated QueryPlan to deterministic catalog search adapter."""

from __future__ import annotations

from decimal import Decimal

from pydantic import ValidationError

from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductRead
from app.schemas.product_filters import (
    ComparisonOperator,
    ProductFilters,
    ProductSortBy,
    SortDirection,
    SpecConstraint,
)
from app.schemas.query_plan import QueryPlan
from app.schemas.sales_functions import ProductSearchResult, ToolStatus

SUPPORTED_NUMERIC_SPECS = {
    "ram_gb",
    "storage_gb",
    "screen_inches",
    "refresh_rate_hz",
}


class ProductSearchTool:
    """Search the catalog without deriving SQL or facts from natural-language text."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def search(
        self,
        plan: QueryPlan,
        *,
        limit: int = 10,
        sort_by: ProductSortBy = ProductSortBy.PRICE,
        sort_direction: SortDirection = SortDirection.ASC,
    ) -> ProductSearchResult:
        unsupported = sorted(
            {item.key for item in plan.specification_constraints}
            - SUPPORTED_NUMERIC_SPECS
        )
        if unsupported:
            return ProductSearchResult(
                status=ToolStatus.INVALID_FILTERS,
                unsupported_filters=unsupported,
                message="The request contains unsupported specification filters.",
            )

        currency = self._normalize_currency(plan.currency)
        if plan.currency is not None and currency is None:
            return ProductSearchResult(
                status=ToolStatus.INVALID_FILTERS,
                unsupported_filters=["currency"],
                message="Only DZD/DA catalog prices are currently supported.",
            )

        try:
            filters = ProductFilters(
                category=plan.category,
                brand=plan.brand,
                min_price=plan.min_price,
                max_price=plan.max_price,
                currency=currency,
                in_stock_only=plan.in_stock_only,
                spec_constraints=[
                    SpecConstraint(
                        key=item.key,
                        operator=ComparisonOperator(item.operator.value),
                        value=item.value,
                    )
                    for item in plan.specification_constraints
                ],
                sort_by=sort_by,
                sort_direction=sort_direction,
            )
        except (ValidationError, ValueError) as error:
            return ProductSearchResult(
                status=ToolStatus.INVALID_FILTERS,
                message=str(error),
            )

        return self.search_filters(filters, limit=limit)

    def search_filters(
        self, filters: ProductFilters, *, limit: int = 10
    ) -> ProductSearchResult:
        """Execute controlled filters, including exact textual CPU/spec constraints."""

        try:
            products = self._repository.search(filters, limit=limit)
        except ValueError as error:
            return ProductSearchResult(
                status=ToolStatus.INVALID_FILTERS,
                message=str(error),
            )
        reads = [ProductRead.model_validate(product) for product in products]
        return ProductSearchResult(
            status=ToolStatus.SUCCESS if reads else ToolStatus.NO_RESULTS,
            products=reads,
        )

    @staticmethod
    def _normalize_currency(currency: str | None) -> str | None:
        if currency is None:
            return None
        normalized = currency.strip().upper()
        return "DZD" if normalized in {"DA", "DZD"} else None


def score_price_suitability(price: Decimal | None, maximum: Decimal | None) -> Decimal:
    """Return a bounded lower-price suitability score for known prices."""

    if price is None or maximum is None or maximum <= 0 or price > maximum:
        return Decimal("0")
    return max(Decimal("0"), min(Decimal("1"), Decimal("1") - price / maximum))
