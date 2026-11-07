"""Quota-free classification for bounded conversational messages."""

from __future__ import annotations

import re

from app.schemas.query_plan import Intent, Language, QueryPlan

_TRIM = re.compile(r"^[\s.,!?؟؛:،]+|[\s.,!?؟؛:،]+$")
_SPACE = re.compile(r"\s+")

_PHRASES: tuple[tuple[Intent, Language, frozenset[str]], ...] = (
    (
        Intent.GREETING,
        Language.EN,
        frozenset({"hi", "hello", "hey", "good morning", "good evening"}),
    ),
    (
        Intent.GREETING,
        Language.FR,
        frozenset({"bonjour", "bonsoir", "salut", "coucou"}),
    ),
    (
        Intent.GREETING,
        Language.AR,
        frozenset({"سلام", "السلام عليكم", "مرحبا", "أهلا", "اهلا"}),
    ),
    (
        Intent.GREETING,
        Language.DZ,
        frozenset({"salam", "salam alikoum", "slm", "wech rak", "wach rak"}),
    ),
    (
        Intent.FAREWELL,
        Language.EN,
        frozenset({"bye", "goodbye", "see you", "see you later"}),
    ),
    (
        Intent.FAREWELL,
        Language.FR,
        frozenset({"au revoir", "à bientôt", "a bientot", "bonne journée"}),
    ),
    (
        Intent.FAREWELL,
        Language.AR,
        frozenset({"مع السلامة", "إلى اللقاء", "الى اللقاء"}),
    ),
    (
        Intent.FAREWELL,
        Language.DZ,
        frozenset({"beslama", "bslama", "بسلامة"}),
    ),
    (
        Intent.GRATITUDE,
        Language.EN,
        frozenset({"thanks", "thank you", "thank you very much", "thx"}),
    ),
    (
        Intent.GRATITUDE,
        Language.FR,
        frozenset({"merci", "merci beaucoup", "je vous remercie"}),
    ),
    (
        Intent.GRATITUDE,
        Language.AR,
        frozenset({"شكرا", "شكراً", "بارك الله فيك"}),
    ),
    (
        Intent.GRATITUDE,
        Language.DZ,
        frozenset({"chokran", "chokrane", "saha", "sahit"}),
    ),
    (
        Intent.HELP,
        Language.EN,
        frozenset({"help", "what can you do", "how can you help", "capabilities"}),
    ),
    (
        Intent.HELP,
        Language.FR,
        frozenset({"aide", "que peux-tu faire", "que pouvez-vous faire", "tu peux faire quoi"}),
    ),
    (
        Intent.HELP,
        Language.AR,
        frozenset({"ماذا يمكنك أن تفعل", "ماذا تستطيع أن تفعل", "كيف يمكنك مساعدتي"}),
    ),
    (
        Intent.HELP,
        Language.DZ,
        frozenset(
            {
                "واش تقدر تدير",
                "وش تقدر تدير",
                "واش تقدري تديري",
                "wach t9der dir",
                "wech t9der dir",
                "chno t9der dir",
            }
        ),
    ),
)


def classify_conversation(message: str) -> QueryPlan | None:
    normalized = _SPACE.sub(" ", _TRIM.sub("", message.casefold())).strip()
    for intent, language, phrases in _PHRASES:
        if normalized in phrases:
            return QueryPlan(
                original_message=message.strip(),
                intent=intent,
                language=language,
                category=None,
                brand=None,
                min_price=None,
                max_price=None,
                currency=None,
                in_stock_only=False,
                specification_constraints=[],
                product_refs=[],
                needs_clarification=False,
                missing_info=[],
                clarification_question=None,
            )
    return None
