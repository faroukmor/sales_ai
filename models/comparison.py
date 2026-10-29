# models/comparison.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ComparisonRow:
    key: str                       # "price" أو مفتاح مواصفة مثل "ram_gb"
    values: tuple[str | None, ...]  # قيمة لكل منتج بنفس الترتيب؛ None = غير مسجَّلة
    differs: bool                  # هل توجد قيمتان مسجَّلتان مختلفتان؟
    has_missing: bool              # هل غابت القيمة عند منتج واحد على الأقل؟


@dataclass(frozen=True)
class ComparisonResult:
    product_names: tuple[str, ...]
    rows: tuple[ComparisonRow, ...]
