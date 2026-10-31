from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.schemas.query_plan import Intent, Language, QueryPlan


def make_plan(message: str, **overrides: Any) -> QueryPlan:
    values: dict[str, Any] = {
        "original_message": message,
        "intent": Intent.PRODUCT_SEARCH,
        "language": Language.EN,
        "category": "laptop",
        "brand": None,
        "min_price": None,
        "max_price": Decimal("100000"),
        "currency": "DZD",
        "in_stock_only": False,
        "specification_constraints": [],
        "product_refs": [],
        "needs_clarification": False,
        "missing_info": [],
        "clarification_question": None,
    }
    values.update(overrides)
    return QueryPlan.model_validate(values)
