# handlers/comparison_handler.py
from models.evidence import EvidenceBundle
from models.query_plan import QueryPlan


class ComparisonHandler:
    def __init__(self, product_repository, comparator):
        self._products = product_repository
        self._comparator = comparator

    def handle(self, plan: QueryPlan) -> EvidenceBundle:
        resolved, missing, ambiguous = [], [], []
        for ref in plan.product_refs:
            matches = self._products.find_by_name(ref)
            if not matches:
                missing.append(ref)
            elif len(matches) > 1:
                ambiguous.append(ref)
            else:
                resolved.append(matches[0])

        unique = list({p.id: p for p in resolved}.values())   # بلا تكرار، وبالترتيب نفسه
        comparison = None
        if not missing and not ambiguous and len(unique) >= 2:
            comparison = self._comparator.compare(unique)
        return EvidenceBundle(
            products=tuple(unique), comparison=comparison,
            missing_refs=tuple(missing), ambiguous_refs=tuple(ambiguous),
        )
