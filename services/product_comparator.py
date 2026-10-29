# services/product_comparator.py
from typing import Sequence

from core.formatting import format_number
from models.comparison import ComparisonResult, ComparisonRow
from models.product import Product, Spec


class ProductComparator:
    """مقارنة حتمية بين منتجات: لا I/O ولا LLM، ولا تخترع قيمًا ناقصة."""

    def compare(self, products: Sequence[Product]) -> ComparisonResult:
        if len(products) < 2:
            raise ValueError("Comparison needs at least two products")

        spec_keys = sorted({key for p in products for key in p.specs})
        rows = [self._row("price", [self._format_price(p) for p in products])]
        rows += [
            self._row(key, [self._format_spec(p.get_spec(key)) for p in products])
            for key in spec_keys
        ]
        return ComparisonResult(
            product_names=tuple(p.name for p in products), rows=tuple(rows)
        )

    @staticmethod
    def _row(key: str, values: list[str | None]) -> ComparisonRow:
        recorded = {v for v in values if v is not None}
        return ComparisonRow(
            key=key,
            values=tuple(values),
            differs=len(recorded) > 1,
            has_missing=any(v is None for v in values),
        )

    @staticmethod
    def _format_price(product: Product) -> str | None:
        if product.price is None:
            return None
        return f"{format_number(product.price)} {product.currency}"

    @staticmethod
    def _format_spec(spec: Spec | None) -> str | None:
        if spec is None:
            return None
        text = spec.value_text
        if text is None and spec.value_num is not None:
            text = format_number(spec.value_num)
        if text is None:
            return None
        return f"{text} {spec.unit}" if spec.unit else text
