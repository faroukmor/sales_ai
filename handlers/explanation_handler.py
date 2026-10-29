# handlers/explanation_handler.py
from models.evidence import EvidenceBundle
from models.query_plan import QueryPlan


class ExplanationHandler:
    def __init__(self, retriever):
        self._retriever = retriever

    def handle(self, plan: QueryPlan) -> EvidenceBundle:
        return EvidenceBundle(chunks=tuple(self._retriever.retrieve(plan.message)))
