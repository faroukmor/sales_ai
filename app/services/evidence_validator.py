"""Validate that public evidence references returned business records."""

from app.agents.state import EvidenceItem, SalesAgentState


class EvidenceValidationError(ValueError):
    pass


class EvidenceValidator:
    def validate(self, state: SalesAgentState) -> list[EvidenceItem]:
        evidence = state.get("evidence", [])
        product_ids = {product.id for product in state.get("products", [])}
        promotion_ids = {promotion.id for promotion in state.get("promotions", [])}
        seen: set[str] = set()
        validated: list[EvidenceItem] = []
        for item in evidence:
            if item.source_id in seen:
                continue
            if item.source_type == "catalog" and item.product_id not in product_ids:
                raise EvidenceValidationError("catalog evidence does not reference a result")
            if item.source_type == "promotion":
                try:
                    promotion_id = int(item.source_id.removeprefix("promotion:"))
                except ValueError as error:
                    raise EvidenceValidationError(
                        "invalid promotion evidence identifier"
                    ) from error
                if promotion_id not in promotion_ids:
                    raise EvidenceValidationError("promotion evidence does not reference a result")
            seen.add(item.source_id)
            validated.append(item)
        return validated
