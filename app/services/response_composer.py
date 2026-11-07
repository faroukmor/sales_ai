"""Grounded multilingual response templates for catalog results."""

from app.agents.state import ExecutionStatus, SalesAgentState
from app.schemas.chat_response import ChatStatus
from app.schemas.query_plan import Intent, Language


class ResponseComposer:
    def compose(self, state: SalesAgentState) -> tuple[str, ChatStatus]:
        plan = state["query_plan"]
        language = plan.language
        if plan.intent is Intent.UNKNOWN:
            return self._text(language, "unsupported_helpful"), ChatStatus.NOT_SUPPORTED
        if plan.needs_clarification:
            return (
                plan.clarification_question or self._text(language, "clarify"),
                ChatStatus.NEEDS_CLARIFICATION,
            )
        if state.get("status") is ExecutionStatus.FAILED:
            code = state.get("errors", [])[-1].code if state.get("errors") else "error"
            if "not_found" in code:
                return self._text(language, "not_found"), ChatStatus.PRODUCT_NOT_FOUND
            if code == "unsupported_intent":
                return self._unsupported(plan.intent, language)
            if code == "insufficient_evidence":
                return self._text(language, "insufficient"), ChatStatus.INSUFFICIENT_EVIDENCE
            return self._text(language, "error"), ChatStatus.ERROR

        count = len(state.get("products", []))
        if plan.intent is Intent.GREETING:
            return self._text(language, "greeting"), ChatStatus.OK
        if plan.intent is Intent.FAREWELL:
            return self._text(language, "farewell"), ChatStatus.OK
        if plan.intent is Intent.GRATITUDE:
            return self._text(language, "gratitude"), ChatStatus.OK
        if plan.intent is Intent.HELP:
            return self._text(language, "help"), ChatStatus.OK
        if plan.intent is Intent.PRODUCT_SEARCH:
            if count == 0:
                return self._text(language, "no_products"), ChatStatus.NO_RESULTS
            return self._count_text(language, "products", count), ChatStatus.OK
        if plan.intent is Intent.COMPARISON:
            return self._text(language, "comparison"), ChatStatus.OK
        if plan.intent is Intent.RECOMMENDATION:
            if not state.get("recommendations"):
                return self._text(language, "no_products"), ChatStatus.NO_RESULTS
            return self._count_text(
                language, "recommendations", len(state["recommendations"])
            ), ChatStatus.OK
        if plan.intent is Intent.PROMOTION_SEARCH:
            if not state.get("promotions"):
                return self._text(language, "no_promotions"), ChatStatus.NO_RESULTS
            return self._count_text(language, "promotions", len(state["promotions"])), ChatStatus.OK
        return self._unsupported(plan.intent, language)

    def _unsupported(self, intent: Intent, language: Language) -> tuple[str, ChatStatus]:
        if intent is Intent.EXPLANATION:
            return self._text(language, "insufficient"), ChatStatus.INSUFFICIENT_EVIDENCE
        return self._text(language, "unsupported_helpful"), ChatStatus.NOT_SUPPORTED

    @staticmethod
    def _lang(language: Language) -> str:
        if language is Language.FR:
            return "fr"
        if language is Language.AR:
            return "ar"
        if language is Language.DZ:
            return "dz"
        return "en"

    def _text(self, language: Language, key: str) -> str:
        texts = {
            "en": {
                "clarify": "Could you provide a little more detail?",
                "not_found": "I could not resolve the requested products.",
                "error": "I could not complete that request safely.",
                "no_products": "No catalog products match all of those requirements.",
                "comparison": "Here is a factual comparison using the catalog data.",
                "no_promotions": "There are no active eligible promotions for that request.",
                "insufficient": "I do not have grounded documentation to answer that question.",
                "unsupported": "That request is not supported by the sales assistant yet.",
                "unsupported_helpful": (
                    "I can help you search products, compare catalog items, recommend options, "
                    "and find active promotions."
                ),
                "greeting": "Hello! How can I help you shop today?",
                "farewell": "Goodbye! I’m here whenever you need help shopping.",
                "gratitude": "You’re welcome! Let me know if you need anything else.",
                "help": (
                    "I can search the catalog, compare products, recommend matching options, "
                    "and show active promotions."
                ),
            },
            "fr": {
                "clarify": "Pouvez-vous préciser votre demande ?",
                "not_found": "Je n’ai pas pu identifier les produits demandés.",
                "error": "Je n’ai pas pu traiter cette demande en toute sécurité.",
                "no_products": "Aucun produit du catalogue ne correspond à tous ces critères.",
                "comparison": "Voici une comparaison factuelle basée sur le catalogue.",
                "no_promotions": "Aucune promotion active et éligible ne correspond.",
                "insufficient": "Je n’ai pas de documentation vérifiée pour répondre.",
                "unsupported": "Cette demande n’est pas encore prise en charge.",
                "unsupported_helpful": (
                    "Je peux rechercher des produits, les comparer, proposer des recommandations "
                    "et afficher les promotions actives."
                ),
                "greeting": "Bonjour ! Comment puis-je vous aider dans vos achats ?",
                "farewell": "Au revoir ! Je reste disponible pour vos prochains achats.",
                "gratitude": "Avec plaisir ! Dites-moi si vous avez besoin d’autre chose.",
                "help": (
                    "Je peux rechercher et comparer des produits, proposer des recommandations "
                    "et afficher les promotions actives."
                ),
            },
            "ar": {
                "clarify": "هل يمكنك توضيح طلبك أكثر؟",
                "not_found": "لم أتمكن من تحديد المنتجات المطلوبة.",
                "error": "تعذر إكمال الطلب بشكل آمن.",
                "no_products": "لا توجد منتجات تطابق كل هذه الشروط.",
                "comparison": "إليك مقارنة مبنية على بيانات الكتالوج.",
                "no_promotions": "لا توجد عروض نشطة ومؤهلة لهذا الطلب.",
                "insufficient": "لا أملك مصادر موثوقة للإجابة عن هذا السؤال.",
                "unsupported": "هذا الطلب غير مدعوم حالياً.",
                "unsupported_helpful": (
                    "يمكنني البحث عن المنتجات ومقارنتها واقتراح خيارات مناسبة "
                    "وعرض التخفيضات النشطة."
                ),
                "greeting": "مرحباً! كيف يمكنني مساعدتك في التسوق اليوم؟",
                "farewell": "مع السلامة! أنا هنا عندما تحتاج إلى مساعدة في التسوق.",
                "gratitude": "العفو! أخبرني إذا احتجت إلى أي مساعدة أخرى.",
                "help": (
                    "يمكنني البحث في الكتالوج ومقارنة المنتجات واقتراح خيارات مناسبة "
                    "وعرض التخفيضات النشطة."
                ),
            },
            "dz": {
                "clarify": "تقدر توضّحلي طلبك أكثر؟",
                "not_found": "ما قدرتش نلقى المنتجات لي طلبتهم.",
                "error": "ما قدرتش نكمل هاد الطلب بأمان.",
                "no_products": "ما كاش منتجات يوافقو كامل الشروط.",
                "comparison": "هادي مقارنة مبنية على معلومات الكتالوج.",
                "no_promotions": "ما كاش تخفيضات نشطة ومناسبة لهاد الطلب.",
                "insufficient": "ما عنديش مصادر موثوقة باش نجاوبك على هاد السؤال.",
                "unsupported": "هاد الطلب مازال ما هوش مدعوم.",
                "unsupported_helpful": (
                    "نقدر نبحثلك على المنتجات، نقارن بينهم، نقترح عليك خيارات، "
                    "ونوريك التخفيضات النشطة."
                ),
                "greeting": "سلام! واش نقدر نعاونك في الشراء اليوم؟",
                "farewell": "بسلامة! راني هنا كي تحتاج مساعدة في الشراء.",
                "gratitude": "بلا مزية! قولّي إذا تحتاج حاجة أخرى.",
                "help": (
                    "نقدر نبحثلك في الكتالوج، نقارن المنتجات، نقترح خيارات مناسبة، "
                    "ونوريك التخفيضات النشطة."
                ),
            },
        }
        return texts[self._lang(language)][key]

    def _count_text(self, language: Language, kind: str, count: int) -> str:
        lang = self._lang(language)
        templates = {
            "products": {
                "en": "I found {count} matching catalog product(s).",
                "fr": "J’ai trouvé {count} produit(s) correspondant(s).",
                "ar": "وجدت {count} منتج مطابق في الكتالوج.",
                "dz": "لقيت {count} منتج مطابق في الكتالوج.",
            },
            "recommendations": {
                "en": "Here are {count} deterministic recommendation(s) matching your constraints.",
                "fr": (
                    "Voici {count} recommandation(s) déterministe(s) "
                    "correspondant à vos critères."
                ),
                "ar": "إليك {count} توصية مرتبة حسب شروطك.",
                "dz": "هاك {count} اقتراح مرتب حسب شروطك.",
            },
            "promotions": {
                "en": "I found {count} active eligible promotion(s).",
                "fr": "J’ai trouvé {count} promotion(s) active(s) et éligible(s).",
                "ar": "وجدت {count} عرض نشط ومؤهل.",
                "dz": "لقيت {count} تخفيض نشط ومناسب.",
            },
        }
        return templates[kind][lang].format(count=count)
