# models/chat_response.py
from dataclasses import dataclass
from enum import Enum

from models.comparison import ComparisonResult
from models.product import Product
from models.promotion import Promotion
from models.query_plan import Intent


class Status(str, Enum):
    OK = "ok"
    NO_RESULTS = "no_results"
    PRODUCT_NOT_FOUND = "product_not_found"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NEEDS_CLARIFICATION = "needs_clarification"
    NOT_SUPPORTED = "not_supported"
    ERROR = "error"


@dataclass(frozen=True)
class Source:
    label: str
    chunk_id: int | None = None


@dataclass(frozen=True)
class ChatResponse:
    answer: str
    intent: Intent
    status: Status
    language: str = "unknown"
    products: tuple[Product, ...] = ()
    sources: tuple[Source, ...] = ()
    promotions: tuple[Promotion, ...] = ()
    comparison: ComparisonResult | None = None
