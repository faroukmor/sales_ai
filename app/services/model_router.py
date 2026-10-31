from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ModelTier(StrEnum):
    FAST = "fast"
    POWERFUL = "powerful"


@dataclass(frozen=True)
class RoutingDecision:
    tier: ModelTier
    reasons: tuple[str, ...]


class ModelRouter:
    """Select a model without spending an additional model call."""

    _intent_patterns = (
        re.compile(r"\b(compare|difference|versus|vs\.?|قارن|قارني)\b", re.IGNORECASE),
        re.compile(r"\b(recommend|suggest|conseille|تنصح|اقترح)\b", re.IGNORECASE),
        re.compile(r"\b(explain|what is|pourquoi|c'est quoi|اشرح|وش هو)\b", re.IGNORECASE),
        re.compile(r"\b(promotion|promo|discount|remise|تخفيض|العروض)\b", re.IGNORECASE),
    )
    _colloquial = re.compile(
        r"\b(3tini|chhal|bghit|n7ab|ma\s*yfout|malyoun|mلاين|ملاين|ملايين|تاع|وش|واش)\b",
        re.IGNORECASE,
    )
    _tradeoffs = re.compile(
        r"\b(but|however|trade.?off|prioriti[sz]e|أفضل.*لكن|mais|par contre|للبرمجة|gaming)\b",
        re.IGNORECASE,
    )
    _ambiguous_reference = re.compile(
        r"\b(this|that|the other|second one|celui-ci|l'autre|هذا|هذي|الثاني|الأخرى)\b",
        re.IGNORECASE,
    )
    _constraint_value = re.compile(
        r"\b\d+(?:[.,]\d+)?\s*(?:gb|go|hz|inch(?:es)?|pouces?|dzd|da)\b",
        re.IGNORECASE,
    )

    def choose(self, message: str) -> RoutingDecision:
        reasons: list[str] = []
        intent_count = sum(bool(pattern.search(message)) for pattern in self._intent_patterns)
        if intent_count >= 2:
            reasons.append("multiple_intentions")
        if self._tradeoffs.search(message):
            reasons.append("preference_tradeoffs")
        if self._colloquial.search(message):
            reasons.append("highly_colloquial")
        if self._ambiguous_reference.search(message) and self._intent_patterns[0].search(message):
            reasons.append("ambiguous_product_references")
        if len(self._constraint_value.findall(message)) >= 3:
            reasons.append("multiple_constraints")

        has_arabic = bool(re.search(r"[\u0600-\u06ff]", message))
        has_latin = bool(re.search(r"[A-Za-z]", message))
        if has_arabic and has_latin and len(message.split()) >= 8:
            reasons.append("complex_mixed_language")

        tier = ModelTier.POWERFUL if reasons else ModelTier.FAST
        return RoutingDecision(tier=tier, reasons=tuple(reasons))

    @staticmethod
    def can_escalate(
        current_tier: ModelTier,
        *,
        fallback_enabled: bool,
        recoverable_failure: bool,
    ) -> bool:
        return (
            current_tier is ModelTier.FAST
            and fallback_enabled
            and recoverable_failure
        )
