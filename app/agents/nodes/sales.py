"""Thin LangGraph nodes for deterministic P6 business functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.agents.state import (
    ComparisonRow,
    ComparisonValue,
    EvidenceItem,
    ExecutionStatus,
    ExecutionStep,
    ProductComparison,
    SalesAgentState,
    StateError,
)
from app.schemas.query_plan import Intent
from app.schemas.sales_functions import ToolStatus
from app.services.recommendation import RecommendationService
from app.tools.product_comparison import ProductComparisonTool
from app.tools.product_search import ProductSearchTool
from app.tools.promotions import PromotionsTool

SalesRoute = Literal[
    "search_products",
    "compare_products",
    "rank_recommendations",
    "lookup_promotions",
    "unsupported_intent",
]


@dataclass(frozen=True)
class SalesFunctionTools:
    search: ProductSearchTool
    comparison: ProductComparisonTool
    recommendations: RecommendationService
    promotions: PromotionsTool


def route_sales_intent(state: SalesAgentState) -> SalesRoute:
    plan = state.get("query_plan")
    intent = state.get("intent") or (plan.intent if plan is not None else None)
    return {
        Intent.PRODUCT_SEARCH: "search_products",
        Intent.COMPARISON: "compare_products",
        Intent.RECOMMENDATION: "rank_recommendations",
        Intent.PROMOTION_SEARCH: "lookup_promotions",
    }.get(intent, "unsupported_intent")


def search_products_node(tools: SalesFunctionTools, state: SalesAgentState) -> SalesAgentState:
    plan = state["query_plan"]
    result = tools.search.search(plan)
    if result.status is ToolStatus.INVALID_FILTERS:
        return _failure(state, ExecutionStep.SEARCH_PRODUCTS, "invalid_filters", result.message)
    products = result.products
    return {
        "products": products,
        "last_product_ids": [product.id for product in products],
        "evidence": [_product_evidence(product.id, product.name) for product in products],
        "status": ExecutionStatus.COMPLETED,
        "current_step": ExecutionStep.SEARCH_PRODUCTS,
    }


def compare_products_node(tools: SalesFunctionTools, state: SalesAgentState) -> SalesAgentState:
    plan = state["query_plan"]
    result = tools.comparison.compare(
        references=plan.product_refs,
        last_product_ids=state.get("last_product_ids", []),
    )
    if result.status is not ToolStatus.SUCCESS:
        return _failure(
            state,
            ExecutionStep.COMPARE_PRODUCTS,
            f"comparison_{result.status.value}",
            "Product references could not be resolved for comparison.",
        )
    comparison = ProductComparison(
        product_ids=[product.id for product in result.products],
        rows=[
            ComparisonRow(
                attribute=row.attribute,
                values=[
                    ComparisonValue(product_id=cell.product_id, value=cell.value)
                    for cell in row.values
                ],
            )
            for row in result.rows
        ],
    )
    return {
        "products": result.products,
        "comparison": comparison,
        "last_product_ids": comparison.product_ids,
        "evidence": [
            _product_evidence(product.id, product.name) for product in result.products
        ],
        "status": ExecutionStatus.COMPLETED,
        "current_step": ExecutionStep.COMPARE_PRODUCTS,
    }


def rank_recommendations_node(
    tools: SalesFunctionTools, state: SalesAgentState
) -> SalesAgentState:
    result = tools.recommendations.recommend(state["query_plan"])
    if result.status not in {ToolStatus.SUCCESS, ToolStatus.NO_RESULTS}:
        return _failure(
            state,
            ExecutionStep.RANK_RECOMMENDATIONS,
            f"recommendation_{result.status.value}",
            result.message,
        )
    products = [item.product for item in result.recommendations]
    evidence = [
        EvidenceItem(
            source_id=f"product:{item.product.id}",
            source_type="catalog",
            product_id=item.product.id,
            content=" ".join(item.reasons) or "Catalog candidate matched hard constraints.",
            url=item.product.url,
        )
        for item in result.recommendations
    ]
    return {
        "recommendations": result.recommendations,
        "products": products,
        "last_product_ids": [product.id for product in products],
        "evidence": evidence,
        "status": ExecutionStatus.COMPLETED,
        "current_step": ExecutionStep.RANK_RECOMMENDATIONS,
    }


def lookup_promotions_node(tools: SalesFunctionTools, state: SalesAgentState) -> SalesAgentState:
    plan = state["query_plan"]
    if not plan.product_refs and plan.category is None and state.get("last_product_ids"):
        result = tools.promotions.lookup(product_ids=state["last_product_ids"])
    else:
        result = tools.promotions.lookup_plan(plan)
    if result.status not in {ToolStatus.SUCCESS, ToolStatus.NO_RESULTS}:
        return _failure(
            state,
            ExecutionStep.RETRIEVE_KNOWLEDGE,
            f"promotion_{result.status.value}",
            result.message,
        )
    return {
        "promotions": result.promotions,
        "evidence": [
            EvidenceItem(
                source_id=f"promotion:{promotion.id}",
                source_type="promotion",
                product_id=promotion.product_id,
                content=promotion.description or "Promotion description is unavailable.",
            )
            for promotion in result.promotions
        ],
        "status": ExecutionStatus.COMPLETED,
        "current_step": ExecutionStep.RETRIEVE_KNOWLEDGE,
    }


def unsupported_intent_node(state: SalesAgentState) -> SalesAgentState:
    return _failure(
        state,
        ExecutionStep.ROUTE_INTENT,
        "unsupported_intent",
        "This intent is not supported by the sales-functions graph.",
    )


def validate_evidence_node(state: SalesAgentState) -> SalesAgentState:
    """Reject evidence lacking a stable source identifier; do not generate claims."""

    evidence = state.get("evidence", [])
    if any(not item.source_id or not item.content for item in evidence):
        return _failure(
            state,
            ExecutionStep.VALIDATE_EVIDENCE,
            "invalid_evidence",
            "Business output contained malformed evidence.",
        )
    return {"current_step": ExecutionStep.VALIDATE_EVIDENCE}


def _failure(
    state: SalesAgentState,
    step: ExecutionStep,
    code: str,
    message: str | None,
) -> SalesAgentState:
    error = StateError(
        code=code,
        message=message or "The business operation could not be completed.",
        step=step,
    )
    return {
        "status": ExecutionStatus.FAILED,
        "current_step": step,
        "errors": [*state.get("errors", []), error],
    }


def _product_evidence(product_id: int, name: str) -> EvidenceItem:
    return EvidenceItem(
        source_id=f"product:{product_id}",
        source_type="catalog",
        product_id=product_id,
        content=f"Catalog record for {name}.",
    )
