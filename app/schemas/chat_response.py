"""Stable public contracts for the GEANT chat API."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agents.state import EvidenceItem, ProductComparison
from app.schemas.product import ProductRead
from app.schemas.promotion import PromotionRead
from app.schemas.query_plan import Intent, Language
from app.schemas.sales_functions import RecommendationItem


class ChatStatus(StrEnum):
    OK = "ok"
    NO_RESULTS = "no_results"
    NEEDS_CLARIFICATION = "needs_clarification"
    PRODUCT_NOT_FOUND = "product_not_found"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_SUPPORTED = "not_supported"
    ERROR = "error"


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, min_length=36, max_length=36)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from uuid import UUID

        parsed = UUID(value)
        if parsed.version != 4 or str(parsed) != value.lower():
            raise ValueError("session_id must be a canonical UUID4")
        return str(parsed)


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    answer: str
    status: ChatStatus
    intent: Intent
    language: Language
    products: list[ProductRead] = Field(default_factory=list)
    comparison: ProductComparison | None = None
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    promotions: list[PromotionRead] = Field(default_factory=list)
    sources: list[EvidenceItem] = Field(default_factory=list)
