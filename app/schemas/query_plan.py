from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Intent(StrEnum):
    PRODUCT_SEARCH = "product_search"
    COMPARISON = "comparison"
    EXPLANATION = "explanation"
    RECOMMENDATION = "recommendation"
    PROMOTION_SEARCH = "promotion_search"
    GREETING = "greeting"
    FAREWELL = "farewell"
    GRATITUDE = "gratitude"
    HELP = "help"
    UNKNOWN = "unknown"


class Language(StrEnum):
    AR = "ar"
    DZ = "dz"
    FR = "fr"
    EN = "en"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class SpecificationOperator(StrEnum):
    EQ = "eq"
    GTE = "gte"
    LTE = "lte"


class QuerySpecificationConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str = Field(min_length=1, max_length=100)
    operator: SpecificationOperator
    value: Decimal
    unit: str | None

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("specification values must be finite")
        return value


class QueryPlan(BaseModel):
    """Untrusted model output after structural, but before business, validation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    original_message: str = Field(min_length=1)
    intent: Intent
    language: Language
    category: str | None
    brand: str | None
    min_price: Decimal | None
    max_price: Decimal | None
    currency: str | None
    in_stock_only: bool
    specification_constraints: list[QuerySpecificationConstraint]
    product_refs: list[str]
    needs_clarification: bool
    missing_info: list[str]
    clarification_question: str | None

    @field_validator("min_price", "max_price")
    @classmethod
    def finite_money(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("monetary values must be finite")
        return value

def groq_query_plan_schema() -> dict[str, Any]:
    """Groq-compatible strict schema; every property is explicitly required."""

    nullable_string = {"type": ["string", "null"]}
    nullable_number = {"type": ["number", "null"]}
    constraint = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "key": {"type": "string"},
            "operator": {"type": "string", "enum": [item.value for item in SpecificationOperator]},
            "value": {"type": "number"},
            "unit": nullable_string,
        },
        "required": ["key", "operator", "value", "unit"],
    }
    properties: dict[str, Any] = {
        "original_message": {"type": "string"},
        "intent": {"type": "string", "enum": [item.value for item in Intent]},
        "language": {"type": "string", "enum": [item.value for item in Language]},
        "category": nullable_string,
        "brand": nullable_string,
        "min_price": nullable_number,
        "max_price": nullable_number,
        "currency": nullable_string,
        "in_stock_only": {"type": "boolean"},
        "specification_constraints": {"type": "array", "items": constraint},
        "product_refs": {"type": "array", "items": {"type": "string"}},
        "needs_clarification": {"type": "boolean"},
        "missing_info": {"type": "array", "items": {"type": "string"}},
        "clarification_question": nullable_string,
    }
    return {
        "title": "query_plan",
        "description": "A grounded intent and filter plan for one customer message.",
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }
