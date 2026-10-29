# handlers/search_handler.py
from models.evidence import EvidenceBundle
from models.query_plan import QueryPlan


class SearchHandler:
    def __init__(self, product_repository):
        self._products = product_repository

    def handle(self, plan: QueryPlan) -> EvidenceBundle:
        return EvidenceBundle(products=tuple(self._products.search(plan.filters)))
