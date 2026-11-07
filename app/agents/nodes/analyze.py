"""Conversation-aware QueryPlan analysis node."""

from __future__ import annotations

from app.agents.state import ExecutionStatus, ExecutionStep, SalesAgentState
from app.schemas.query_plan import Intent, QueryPlan
from app.services.conversation_classifier import classify_conversation
from app.services.intent_parser import IntentParser

FOLLOW_UP_MARKERS = (
    "only those",
    "only with",
    "seulement",
    "ceux avec",
    "فقط",
    "غير",
    "برك",
)


def analyze_request_node(parser: IntentParser, state: SalesAgentState) -> SalesAgentState:
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("chat state has no message to analyze")
    message = messages[-1].content
    if not isinstance(message, str):
        raise ValueError("chat message content must be text")
    previous = state.get("query_plan")
    plan = classify_conversation(message) or parser.parse(message).plan
    plan = _apply_session_context(plan, previous, state.get("last_product_ids", []))
    return {
        "query_plan": plan,
        "intent": plan.intent,
        "language": plan.language,
        "missing_info": list(plan.missing_info),
        "status": (
            ExecutionStatus.NEEDS_CLARIFICATION
            if plan.needs_clarification
            else ExecutionStatus.RUNNING
        ),
        "current_step": ExecutionStep.ANALYZE_REQUEST,
        "errors": [],
        "products": [],
        "comparison": None,
        "promotions": [],
        "recommendations": [],
        "evidence": [],
    }


def _apply_session_context(
    plan: QueryPlan,
    previous: QueryPlan | None,
    last_product_ids: list[int],
) -> QueryPlan:
    if plan.intent is Intent.COMPARISON and len(last_product_ids) >= 2:
        return plan.model_copy(
            update={
                "needs_clarification": False,
                "missing_info": [],
                "clarification_question": None,
            }
        )
    normalized = plan.original_message.casefold()
    is_follow_up = any(marker in normalized for marker in FOLLOW_UP_MARKERS)
    if (
        is_follow_up
        and previous is not None
        and plan.intent is Intent.PRODUCT_SEARCH
        and previous.intent in {Intent.PRODUCT_SEARCH, Intent.RECOMMENDATION}
    ):
        old_constraints = {item.key: item for item in previous.specification_constraints}
        old_constraints.update({item.key: item for item in plan.specification_constraints})
        return plan.model_copy(
            update={
                "category": plan.category or previous.category,
                "brand": plan.brand or previous.brand,
                "min_price": plan.min_price if plan.min_price is not None else previous.min_price,
                "max_price": plan.max_price if plan.max_price is not None else previous.max_price,
                "currency": plan.currency or previous.currency,
                "in_stock_only": plan.in_stock_only or previous.in_stock_only,
                "specification_constraints": list(old_constraints.values()),
            }
        )
    return plan
