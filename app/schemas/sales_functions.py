"""Structured, API-safe outputs for deterministic sales functions."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductRead
from app.schemas.promotion import PromotionRead


class ToolStatus(StrEnum):
    SUCCESS = "success"
    NO_RESULTS = "no_results"
    INVALID_FILTERS = "invalid_filters"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class ProductSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ToolStatus
    products: list[ProductRead] = Field(default_factory=list)
    unsupported_filters: list[str] = Field(default_factory=list)
    message: str | None = None


class ComparisonCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int
    value: str


class ComparisonRowResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attribute: str
    values: list[ComparisonCell]


class ProductComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ToolStatus
    products: list[ProductRead] = Field(default_factory=list)
    rows: list[ComparisonRowResult] = Field(default_factory=list)
    unresolved_references: list[str] = Field(default_factory=list)
    ambiguous_references: dict[str, list[int]] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    product: ProductRead
    score: Decimal = Field(ge=0, le=1)
    reasons: list[str]
    missing_specifications: list[str]


class RecommendationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ToolStatus
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    scoring_weights: dict[str, Decimal] = Field(default_factory=dict)
    message: str | None = None


class PromotionLookupResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ToolStatus
    promotions: list[PromotionRead] = Field(default_factory=list)
    incomplete_promotion_ids: list[int] = Field(default_factory=list)
    message: str | None = None
