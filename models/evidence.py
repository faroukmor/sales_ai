# models/evidence.py
from dataclasses import dataclass

from models.chunk import ScoredChunk
from models.comparison import ComparisonResult
from models.product import Product
from models.promotion import Promotion


@dataclass(frozen=True)
class EvidenceBundle:
    """كل ما جمعه الـ handler من مصادر موثوقة. لا منطق هنا، بيانات فقط."""
    products: tuple[Product, ...] = ()
    chunks: tuple[ScoredChunk, ...] = ()
    promotions: tuple[Promotion, ...] = ()
    comparison: ComparisonResult | None = None
    missing_refs: tuple[str, ...] = ()     # أسماء لم تُطابق أي منتج
    ambiguous_refs: tuple[str, ...] = ()   # أسماء طابقت عدة منتجات
