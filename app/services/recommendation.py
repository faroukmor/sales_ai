"""Deterministic, explainable product recommendation ranking."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductRead
from app.schemas.query_plan import QueryPlan
from app.schemas.sales_functions import (
    RecommendationItem,
    RecommendationResult,
    ToolStatus,
)
from app.tools.product_search import ProductSearchTool, score_price_suitability

DEFAULT_WEIGHTS = {
    "price": Decimal("0.35"),
    "specifications": Decimal("0.45"),
    "availability": Decimal("0.20"),
}
RELEVANT_SPEC_KEYS = ("ram_gb", "storage_gb", "processor")


class RecommendationService:
    """Rank database candidates after all QueryPlan hard constraints are enforced."""

    def __init__(
        self,
        repository: ProductRepository,
        *,
        weights: dict[str, Decimal] | None = None,
    ) -> None:
        self._repository = repository
        self._search = ProductSearchTool(repository)
        self._weights = weights or DEFAULT_WEIGHTS.copy()
        if set(self._weights) != set(DEFAULT_WEIGHTS):
            raise ValueError("weights must define price, specifications, and availability")
        if sum(self._weights.values()) != Decimal("1"):
            raise ValueError("recommendation weights must sum to 1")
        if any(weight < 0 for weight in self._weights.values()):
            raise ValueError("recommendation weights must be non-negative")

    def recommend(self, plan: QueryPlan, *, top_k: int = 3) -> RecommendationResult:
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        if plan.needs_clarification:
            return RecommendationResult(
                status=ToolStatus.INSUFFICIENT_INFORMATION,
                scoring_weights=self._weights,
                message=plan.clarification_question or "The requirements need clarification.",
            )

        search = self._search.search(plan, limit=100)
        if search.status is ToolStatus.INVALID_FILTERS:
            return RecommendationResult(
                status=ToolStatus.INVALID_FILTERS,
                scoring_weights=self._weights,
                message=search.message,
            )
        if not search.products:
            return RecommendationResult(
                status=ToolStatus.NO_RESULTS,
                scoring_weights=self._weights,
                message="No products satisfy all hard constraints.",
            )

        scored = [self._score(product, plan) for product in search.products]
        scored.sort(key=lambda item: (-item[0], item[1].id))
        recommendations = [
            RecommendationItem(
                rank=index,
                product=product,
                score=score,
                reasons=reasons,
                missing_specifications=missing,
            )
            for index, (score, product, reasons, missing) in enumerate(
                scored[:top_k], start=1
            )
        ]
        return RecommendationResult(
            status=ToolStatus.SUCCESS,
            recommendations=recommendations,
            scoring_weights=self._weights,
        )

    def _score(
        self, product: ProductRead, plan: QueryPlan
    ) -> tuple[Decimal, ProductRead, list[str], list[str]]:
        price_score = score_price_suitability(product.price, plan.max_price)
        if plan.max_price is None:
            price_score = Decimal("1") if product.price is not None else Decimal("0")

        requested = [constraint.key for constraint in plan.specification_constraints]
        available = {
            spec.key
            for spec in product.specs
            if spec.value_num is not None or spec.value_text
        }
        spec_score = (
            Decimal("1")
            if not requested
            else Decimal(sum(key in available for key in requested)) / Decimal(len(requested))
        )
        availability_score = Decimal("1") if product.in_stock is True else Decimal("0")
        score = (
            price_score * self._weights["price"]
            + spec_score * self._weights["specifications"]
            + availability_score * self._weights["availability"]
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        reasons: list[str] = []
        if product.price is not None:
            reasons.append(
                "Price is within the hard budget."
                if plan.max_price is not None
                else "Product has a known catalog price."
            )
        if requested:
            reasons.append("All requested technical constraints are satisfied.")
        if product.in_stock is True:
            reasons.append("Product is currently marked in stock.")
        missing = [key for key in RELEVANT_SPEC_KEYS if key not in available]
        return score, product, reasons, missing
