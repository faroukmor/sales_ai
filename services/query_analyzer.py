# services/query_analyzer.py
import re

from models.query_plan import Comparison, Intent, ProductFilters, QueryPlan, SpecConstraint

# أرقام عربية-هندية وفارسية -> أرقام لاتينية
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# افتراض: فئات الكتالوج التجريبي فقط. ستُستبدل بفئات الكتالوج الحقيقي لاحقًا.
CATEGORY_SYNONYMS = {
    "laptop": ("laptop", "laptops", "notebook", "notebooks"),
    "tv": ("tv", "tvs", "television", "televisions"),
}

_FRENCH_WORDS = frozenset({
    "le", "la", "les", "des", "une", "pour", "avec", "moins", "quel", "quelle",
    "quels", "je", "cherche", "ordinateur", "prix",
})

# رقم: 100,000 أو 100.000 (فواصل آلاف) أو 100000 أو 1.5
_NUM = r"\d{1,3}(?:[,.]\d{3})+(?!\d)|\d+(?:\.\d+)?"
_CUR = r"(?:dzd|da|dinars?)"

_RAM = r"ram|memory"
_STORAGE = r"ssd|hdd|storage|disk"
_SPEC_RE = re.compile(
    rf"(?P<num>{_NUM})\s*(?P<unit>tb|gb)\s*(?:of\s+)?(?P<kind>{_RAM}|{_STORAGE})\b"
    rf"|\b(?P<kind2>{_RAM}|{_STORAGE})\s*(?:of\s+)?(?P<num2>{_NUM})\s*(?P<unit2>tb|gb)\b"
)
_INCH_RE = re.compile(rf'(?P<num>{_NUM})\s*(?:inch(?:es)?|")')

_MAX_Q = (r"(?:under|below|less than|cheaper than|at most|up to|max(?:imum)?(?: price)?(?: of)?"
          r"|no more than|within|not exceeding|budget(?: of| is)?)")
_MIN_Q = (r"(?:over|above|more than|at least|minimum(?: price)?(?: of)?|min(?: price)?(?: of)?"
          r"|starting (?:at|from))")
_AMOUNT = rf"(?P<amount>{_NUM})\s*(?P<k>k\b)?\s*(?P<cur>{_CUR}\b)?"
_MAX_RE = re.compile(rf"\b{_MAX_Q}\s+(?:an?\s+)?(?:price\s+of\s+)?{_AMOUNT}")
_MIN_RE = re.compile(rf"\b{_MIN_Q}\s+(?:an?\s+)?(?:price\s+of\s+)?{_AMOUNT}")
_RANGE_RE = re.compile(
    rf"\b(?:between|from)\s+(?P<a>{_NUM})\s*(?P<ak>k\b)?\s*(?:{_CUR}\b)?\s+(?:and|to)\s+"
    rf"(?P<b>{_NUM})\s*(?P<bk>k\b)?\s*(?P<cur>{_CUR}\b)?"
)
_BARE_AMOUNT_RE = re.compile(rf"(?P<amount>{_NUM})\s*(?P<k>k\b)?\s*{_CUR}\b")

_COMPARE_RE = re.compile(r"\b(compare|comparison|versus|vs)\b")
_PROMO_RE = re.compile(r"\b(promo|promos|promotion|promotions|offer|offers|deal|deals|discount|discounts)\b")
_RECOMMEND_RE = re.compile(
    r"\b(recommend|recommendation|recommendations|suggest|suggestion)\b"
    r"|\bwhich\b.*\b(?:should|do) i\b|\bwhat should i (?:buy|get|choose)\b"
)
_STRONG_EXPLAIN_RE = re.compile(r"\b(explain|difference between|meaning of|how does|how do|why|define)\b")
_WEAK_EXPLAIN_RE = re.compile(r"^\s*(?:what is|what are|what's|whats)\b")
_SEARCH_VERB_RE = re.compile(r"\b(find|search|show|looking for|look for|need|want|buy|list|get me)\b")
_IN_STOCK_RE = re.compile(r"\b(in stock|available|availability)\b")

# أطول عبارة أولًا، حتى يغلب "no more than" على "more than"
_BEFORE_QUALIFIERS = sorted([
    ("at least", Comparison.GTE), ("minimum of", Comparison.GTE), ("minimum", Comparison.GTE),
    ("min", Comparison.GTE), ("more than", Comparison.GTE), ("greater than", Comparison.GTE),
    ("over", Comparison.GTE), ("above", Comparison.GTE),
    ("at most", Comparison.LTE), ("maximum of", Comparison.LTE), ("maximum", Comparison.LTE),
    ("max", Comparison.LTE), ("up to", Comparison.LTE), ("no more than", Comparison.LTE),
    ("less than", Comparison.LTE), ("under", Comparison.LTE), ("below", Comparison.LTE),
], key=lambda item: -len(item[0]))
_AFTER_QUALIFIERS = (
    ("or more", Comparison.GTE), ("or higher", Comparison.GTE), ("or above", Comparison.GTE),
    ("+", Comparison.GTE),
    ("or less", Comparison.LTE), ("or lower", Comparison.LTE), ("or below", Comparison.LTE),
)

_SPLIT_REFS_RE = re.compile(r"\s*(?:,|\band\b|\bvs\.?|\bversus\b|\bwith\b)\s*", re.I)


def detect_language(text: str) -> str:
    """"ar" إن وُجدت حروف عربية، "fr" إن وُجدت كلمات فرنسية شائعة، وإلا "en"."""
    if not any(ch.isalpha() for ch in text):
        return "unknown"
    if re.search(r"[\u0600-\u06FF]", text):
        return "ar"
    words = set(re.findall(r"[a-zàâçéèêëîïôûùüÿœ']+", text.lower()))
    return "fr" if words & _FRENCH_WORDS else "en"


def _parse_number(token: str) -> float:
    if re.fullmatch(r"\d{1,3}(?:[,.]\d{3})+", token):
        return float(re.sub(r"[,.]", "", token))
    return float(token)


def _comparison_near(text: str, start: int, end: int) -> Comparison:
    """يستنتج "على الأقل / على الأكثر" من الكلمات المجاورة. الافتراض عند الغياب: GTE."""
    after = text[end:end + 12].lstrip()
    for phrase, op in _AFTER_QUALIFIERS:
        if after.startswith(phrase):
            return op
    before = text[max(0, start - 20):start].rstrip()
    for phrase, op in _BEFORE_QUALIFIERS:
        if before.endswith(phrase):
            head = before[: len(before) - len(phrase)]
            if not head or not head[-1].isalpha():
                return op
    return Comparison.GTE


def _mask(chars: list[str], start: int, end: int) -> None:
    for i in range(start, end):
        chars[i] = " "


def _plausible_price(value: float, has_marker: bool) -> bool:
    """رقم صغير بلا عملة ولا "k" ليس سعرًا غالبًا (مثل "under 5 stars")."""
    return has_marker or value >= 1000


class QueryAnalyzer:
    """يحوّل الرسالة إلى QueryPlan بقواعد (rules) حتمية. لا يستعلم قاعدة البيانات."""

    def __init__(self, known_brands: tuple[str, ...] | list[str] = ()):
        self._brands = tuple(known_brands)
        self._category_res = {
            category: re.compile(r"\b(?:" + "|".join(map(re.escape, words)) + r")\b")
            for category, words in CATEGORY_SYNONYMS.items()
        }

    def analyze(self, message: str) -> QueryPlan:
        text = message.translate(_DIGITS).strip()
        language = detect_language(text)
        if not text:
            return QueryPlan(message=message, language="unknown")
        lowered = text.lower()

        spec_constraints, work = self._extract_specs(lowered)
        min_price, max_price, leftover_amount, work = self._extract_prices(work)
        category = self._extract_category(lowered)
        brand = self._extract_brand(lowered)
        in_stock_only = bool(_IN_STOCK_RE.search(lowered))
        has_constraints = bool(spec_constraints) or min_price is not None or max_price is not None

        intent = self._detect_intent(lowered, category, has_constraints, leftover_amount)
        refs: tuple[str, ...] = ()
        missing: list[str] = []
        if intent is Intent.COMPARISON:
            refs = self._extract_refs(text)
            if len(refs) < 2:
                missing.append("products_to_compare")
        elif intent in (Intent.PRODUCT_SEARCH, Intent.RECOMMENDATION):
            if category is None:
                missing.append("category")
            if leftover_amount and intent is Intent.PRODUCT_SEARCH:
                missing.append("price_bound")

        return QueryPlan(
            message=message,
            intent=intent,
            language=language,
            filters=ProductFilters(
                category=category, brand=brand, min_price=min_price, max_price=max_price,
                in_stock_only=in_stock_only, spec_constraints=spec_constraints,
            ),
            product_refs=refs,
            missing_info=tuple(missing),
        )

    # ---------- النية ----------

    @staticmethod
    def _detect_intent(lowered, category, has_constraints, leftover_amount) -> Intent:
        if _COMPARE_RE.search(lowered):
            return Intent.COMPARISON
        if _PROMO_RE.search(lowered):
            return Intent.PROMOTION_SEARCH
        if _RECOMMEND_RE.search(lowered):
            return Intent.RECOMMENDATION
        if _STRONG_EXPLAIN_RE.search(lowered):
            return Intent.EXPLANATION
        if _WEAK_EXPLAIN_RE.search(lowered) and not has_constraints:
            return Intent.EXPLANATION
        if category or has_constraints or leftover_amount or _SEARCH_VERB_RE.search(lowered):
            return Intent.PRODUCT_SEARCH
        return Intent.UNKNOWN

    # ---------- المواصفات ----------

    @staticmethod
    def _extract_specs(text: str) -> tuple[tuple[SpecConstraint, ...], str]:
        constraints: list[SpecConstraint] = []
        masked = list(text)
        for m in _SPEC_RE.finditer(text):
            value = _parse_number(m.group("num") or m.group("num2"))
            if (m.group("unit") or m.group("unit2")) == "tb":
                value *= 1024
            kind = m.group("kind") or m.group("kind2")
            key = "ram_gb" if kind in ("ram", "memory") else "storage_gb"
            constraints.append(SpecConstraint(key, _comparison_near(text, m.start(), m.end()), value))
            _mask(masked, m.start(), m.end())
        for m in _INCH_RE.finditer(text):
            value = _parse_number(m.group("num"))
            constraints.append(
                SpecConstraint("screen_inches", _comparison_near(text, m.start(), m.end()), value)
            )
            _mask(masked, m.start(), m.end())
        return tuple(constraints), "".join(masked)

    # ---------- الأسعار ----------

    @staticmethod
    def _amount(number: str, k: str | None) -> float:
        return _parse_number(number) * (1000 if k else 1)

    def _extract_prices(self, text: str):
        masked = list(text)
        min_price = max_price = None

        m = _RANGE_RE.search(text)
        if m:
            a, b = self._amount(m.group("a"), m.group("ak")), self._amount(m.group("b"), m.group("bk"))
            marker = bool(m.group("cur") or m.group("ak") or m.group("bk"))
            if _plausible_price(max(a, b), marker):
                min_price, max_price = sorted((a, b))
                _mask(masked, m.start(), m.end())

        current = "".join(masked)
        if max_price is None:
            m = _MAX_RE.search(current)
            if m:
                value = self._amount(m.group("amount"), m.group("k"))
                if _plausible_price(value, bool(m.group("k") or m.group("cur"))):
                    max_price = value
                    _mask(masked, m.start(), m.end())
        current = "".join(masked)
        if min_price is None:
            m = _MIN_RE.search(current)
            if m:
                value = self._amount(m.group("amount"), m.group("k"))
                if _plausible_price(value, bool(m.group("k") or m.group("cur"))):
                    min_price = value
                    _mask(masked, m.start(), m.end())

        remaining = "".join(masked)
        leftover = any(
            _plausible_price(self._amount(m.group("amount"), m.group("k")), True)
            for m in _BARE_AMOUNT_RE.finditer(remaining)
        )
        return min_price, max_price, leftover, remaining

    # ---------- الفئة والعلامة والمنتجات ----------

    def _extract_category(self, lowered: str) -> str | None:
        for category, pattern in self._category_res.items():
            if pattern.search(lowered):
                return category
        return None

    def _extract_brand(self, lowered: str) -> str | None:
        for brand in self._brands:
            if re.search(rf"\b{re.escape(brand.lower())}\b", lowered):
                return brand
        return None

    @staticmethod
    def _extract_refs(text: str) -> tuple[str, ...]:
        m = re.search(r"\b(?:compare|comparison)\b(?:\s+(?:of|between))?\s*(?P<rest>.*)$", text, re.I)
        rest = m.group("rest") if m else text
        refs: list[str] = []
        for part in _SPLIT_REFS_RE.split(rest):
            name = re.sub(r"^the\s+", "", part.strip().rstrip("?.! ").strip(), flags=re.I)
            if name and name.lower() not in {r.lower() for r in refs}:
                refs.append(name)
        return tuple(refs)
