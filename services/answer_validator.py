# services/answer_validator.py
import re
from dataclasses import dataclass
from typing import Sequence

from core.formatting import format_number

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_NUMBER_RE = re.compile(r"\d{1,3}(?:[,.]\d{3})+(?!\d)|\d+(?:[.,]\d+)?")
_LIST_MARKER_RE = re.compile(r"(?m)^\s*\d+[.)]\s+")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    unsupported_numbers: tuple[str, ...] = ()


def _normalize(token: str) -> str:
    if re.fullmatch(r"\d{1,3}(?:[,.]\d{3})+", token):
        return format_number(float(re.sub(r"[,.]", "", token)))
    return format_number(float(token.replace(",", ".")))


def numbers_in(text: str) -> set[str]:
    text = _LIST_MARKER_RE.sub("", text.translate(_DIGITS))   # نتجاهل ترقيم القوائم "1. ..."
    return {_normalize(token) for token in _NUMBER_RE.findall(text)}


class AnswerValidator:
    """فحص حتمي: كل رقم في إجابة النموذج يجب أن يظهر في الأدلة.

    هذا فحص مساعد وليس إثباتًا للصحة: لا يلتقط الأرقام المكتوبة حروفًا
    ولا الأخطاء غير الرقمية.
    """

    def validate(self, answer: str, evidence_texts: Sequence[str]) -> ValidationResult:
        evidence_numbers: set[str] = set()
        for text in evidence_texts:
            evidence_numbers |= numbers_in(text)
        unsupported = tuple(sorted(n for n in numbers_in(answer) if n not in evidence_numbers))
        return ValidationResult(ok=not unsupported, unsupported_numbers=unsupported)
