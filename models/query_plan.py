# models/query_plan.py
from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    PRODUCT_SEARCH = "product_search"
    EXPLANATION = "explanation"
    COMPARISON = "comparison"
    RECOMMENDATION = "recommendation"
    PROMOTION_SEARCH = "promotion_search"
    UNKNOWN = "unknown"


class Comparison(str, Enum):
    GTE = "gte"
    LTE = "lte"
    EQ = "eq"


@dataclass(frozen=True)
class SpecConstraint:
    key: str
    op: Comparison
    value: float


@dataclass(frozen=True)
class ProductFilters:
    category: str | None = None
    brand: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    in_stock_only: bool = False
    spec_constraints: tuple[SpecConstraint, ...] = ()


@dataclass(frozen=True)
class QueryPlan:
    message: str
    intent: Intent = Intent.UNKNOWN
    language: str = "unknown"
    filters: ProductFilters = ProductFilters()
    product_refs: tuple[str, ...] = ()
    missing_info: tuple[str, ...] = ()
