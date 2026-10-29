# handlers/__init__.py
from typing import Protocol

from models.evidence import EvidenceBundle
from models.query_plan import QueryPlan


class Handler(Protocol):
    """كل handler يجمع الأدلة لنية واحدة ويرجع EvidenceBundle."""

    def handle(self, plan: QueryPlan) -> EvidenceBundle: ...
