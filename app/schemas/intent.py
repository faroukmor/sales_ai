from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.query_plan import (
    Intent,
    Language,
    QuerySpecificationConstraint,
)


class IntentParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=2000)


class IntentFiltersResponse(BaseModel):
    category: str | None
    brand: str | None
    min_price: Decimal | None
    max_price: Decimal | None
    currency: str | None
    in_stock_only: bool
    specification_constraints: list[QuerySpecificationConstraint]


class IntentParseResponse(BaseModel):
    original_message: str
    intent: Intent
    language: Language
    filters: IntentFiltersResponse
    product_refs: list[str]
    needs_clarification: bool
    missing_info: list[str]
    clarification_question: str | None
    model_used: str
    escalated: bool
    latency_ms: float
    token_usage: dict[str, int]
