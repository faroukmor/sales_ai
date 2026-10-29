# models/promotion.py
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Promotion:
    id: int
    title: str
    source: str
    starts_at: date | None = None
    ends_at: date | None = None
    conditions: str | None = None
    product_id: int | None = None
    category: str | None = None
