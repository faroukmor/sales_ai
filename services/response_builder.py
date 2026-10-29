# services/response_builder.py
from models.chat_response import ChatResponse, Source, Status
from models.evidence import EvidenceBundle
from models.query_plan import Intent, QueryPlan

_T = {
    "found_products": {
        "en": "I found {count} matching product(s). Prices and availability come from the product catalogue.",
        "fr": "J'ai trouvé {count} produit(s) correspondant(s). Les prix et la disponibilité proviennent du catalogue.",
        "ar": "وجدتُ {count} منتج(ات) مطابقة. الأسعار والتوفر مأخوذة من كتالوج المنتجات.",
    },
    "no_results": {
        "en": "No products match these conditions. You could try raising the budget or relaxing a requirement.",
        "fr": "Aucun produit ne correspond à ces critères. Essayez d'augmenter le budget ou d'assouplir une exigence.",
        "ar": "لا توجد منتجات تطابق هذه الشروط. يمكنك رفع الميزانية أو تخفيف أحد الشروط.",
    },
    "products_not_found": {
        "en": "I couldn't find these products in the catalogue: {names}.",
        "fr": "Je n'ai pas trouvé ces produits dans le catalogue : {names}.",
        "ar": "لم أجد هذه المنتجات في الكتالوج: {names}.",
    },
    "ambiguous": {
        "en": "\"{names}\" matches several products. Could you give the full product name?",
        "fr": "« {names} » correspond à plusieurs produits. Pouvez-vous donner le nom complet ?",
        "ar": "«{names}» ينطبق على عدة منتجات. هل يمكنك كتابة الاسم الكامل للمنتج؟",
    },
    "comparison_intro": {
        "en": "Comparison of {names}. \"{na}\" means the value is not recorded in the catalogue.",
        "fr": "Comparaison de {names}. « {na} » signifie que la valeur n'est pas renseignée dans le catalogue.",
        "ar": "مقارنة بين {names}. «{na}» تعني أن القيمة غير مسجَّلة في الكتالوج.",
    },
    "na": {"en": "n/a", "fr": "n/d", "ar": "غير متوفر"},
    "insufficient_evidence": {
        "en": "I don't have enough reliable information to answer this question.",
        "fr": "Je n'ai pas assez d'informations fiables pour répondre à cette question.",
        "ar": "لا أملك معلومات موثوقة كافية للإجابة عن هذا السؤال.",
    },
    "clarify_category": {
        "en": "Which kind of product are you looking for (for example a laptop or a TV)?",
        "fr": "Quel type de produit recherchez-vous (par exemple un ordinateur portable ou un téléviseur) ?",
        "ar": "ما نوع المنتج الذي تبحث عنه (مثل حاسوب محمول أو تلفاز)؟",
    },
    "clarify_compare": {
        "en": "Which products would you like to compare? Please name at least two.",
        "fr": "Quels produits souhaitez-vous comparer ? Indiquez-en au moins deux.",
        "ar": "ما المنتجات التي تريد مقارنتها؟ اذكر منتجين على الأقل.",
    },
    "clarify_price_bound": {
        "en": "Is that amount your maximum budget or your minimum?",
        "fr": "Ce montant est-il votre budget maximum ou minimum ?",
        "ar": "هل هذا المبلغ هو ميزانيتك القصوى أم الدنيا؟",
    },
    "clarify_unknown": {
        "en": "I'm not sure I understood. I can search for products, compare them, explain specifications and find promotions.",
        "fr": "Je ne suis pas sûr d'avoir compris. Je peux chercher des produits, les comparer, expliquer des caractéristiques et trouver des promotions.",
        "ar": "لم أتأكد أنني فهمت طلبك. يمكنني البحث عن المنتجات ومقارنتها وشرح مواصفاتها وإيجاد العروض.",
    },
    "error": {
        "en": "Something went wrong while handling your request. Please try again.",
        "fr": "Une erreur est survenue lors du traitement de votre demande. Veuillez réessayer.",
        "ar": "حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى.",
    },
    "not_supported": {
        "en": "This type of request is not supported yet.",
        "fr": "Ce type de demande n'est pas encore pris en charge.",
        "ar": "هذا النوع من الطلبات غير مدعوم بعد.",
    },
}

_CLARIFY_KEY_BY_MISSING = {
    "category": "clarify_category",
    "products_to_compare": "clarify_compare",
    "price_bound": "clarify_price_bound",
}


class ResponseBuilder:
    """يحوّل (خطة + أدلة + نص مولَّد اختياري) إلى ChatResponse. لا LLM ولا I/O."""

    def build(self, plan: QueryPlan, bundle: EvidenceBundle,
              generated_text: str | None = None) -> ChatResponse:
        if plan.intent is Intent.PRODUCT_SEARCH:
            return self._search(plan, bundle)
        if plan.intent is Intent.COMPARISON:
            return self._comparison(plan, bundle)
        if plan.intent is Intent.EXPLANATION:
            return self._explanation(plan, bundle, generated_text)
        return self.unsupported(plan)

    def needs_clarification(self, plan: QueryPlan) -> ChatResponse:
        key = "clarify_unknown"
        if plan.missing_info:
            key = _CLARIFY_KEY_BY_MISSING.get(plan.missing_info[0], "clarify_unknown")
        return self._make(plan, Status.NEEDS_CLARIFICATION, self._t(key, plan.language))

    def error(self, plan: QueryPlan) -> ChatResponse:
        return self._make(plan, Status.ERROR, self._t("error", plan.language))

    def unsupported(self, plan: QueryPlan) -> ChatResponse:
        return self._make(plan, Status.NOT_SUPPORTED, self._t("not_supported", plan.language))

    # ---------- حسب النية ----------

    def _search(self, plan, bundle) -> ChatResponse:
        if not bundle.products:
            return self._make(plan, Status.NO_RESULTS, self._t("no_results", plan.language))
        answer = self._t("found_products", plan.language, count=len(bundle.products))
        return self._make(plan, Status.OK, answer, products=bundle.products)

    def _comparison(self, plan, bundle) -> ChatResponse:
        lang = plan.language
        if bundle.ambiguous_refs:
            names = ", ".join(bundle.ambiguous_refs)
            return self._make(plan, Status.NEEDS_CLARIFICATION, self._t("ambiguous", lang, names=names))
        if bundle.missing_refs:
            names = ", ".join(bundle.missing_refs)
            return self._make(plan, Status.PRODUCT_NOT_FOUND, self._t("products_not_found", lang, names=names))
        if bundle.comparison is None:
            return self._make(plan, Status.NEEDS_CLARIFICATION, self._t("clarify_compare", lang))

        na = self._t("na", lang)
        lines = [self._t("comparison_intro", lang, names=" / ".join(bundle.comparison.product_names), na=na)]
        for row in bundle.comparison.rows:
            lines.append(f"{row.key}: " + " | ".join(v if v is not None else na for v in row.values))
        return self._make(plan, Status.OK, "\n".join(lines),
                          products=bundle.products, comparison=bundle.comparison)

    def _explanation(self, plan, bundle, generated_text) -> ChatResponse:
        if not generated_text or not bundle.chunks:
            return self._make(plan, Status.INSUFFICIENT_EVIDENCE, self._t("insufficient_evidence", plan.language))
        seen: set[int] = set()
        sources: list[Source] = []
        for scored in bundle.chunks:
            if scored.chunk.id not in seen:
                seen.add(scored.chunk.id)
                sources.append(Source(label=scored.chunk.title or scored.chunk.source,
                                      chunk_id=scored.chunk.id))
        return self._make(plan, Status.OK, generated_text, sources=tuple(sources))

    # ---------- مساعدات ----------

    @staticmethod
    def _t(key: str, language: str, **values) -> str:
        variants = _T[key]
        return variants.get(language, variants["en"]).format(**values)

    @staticmethod
    def _make(plan: QueryPlan, status: Status, answer: str, **fields) -> ChatResponse:
        return ChatResponse(answer=answer, intent=plan.intent, status=status,
                            language=plan.language, **fields)
