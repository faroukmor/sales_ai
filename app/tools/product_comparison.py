"""Database-grounded structured product comparison."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from app.db.models import Product
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_repository import PromotionRepository
from app.schemas.product import ProductRead
from app.schemas.sales_functions import (
    ComparisonCell,
    ComparisonRowResult,
    ProductComparisonResult,
    ToolStatus,
)

COMPARISON_SPEC_KEYS = (
    "ram_gb",
    "storage_gb",
    "processor",
    "screen_inches",
    "resolution",
    "display_type",
    "refresh_rate_hz",
)


class ProductComparisonTool:
    def __init__(
        self,
        product_repository: ProductRepository,
        promotion_repository: PromotionRepository | None = None,
    ) -> None:
        self._products = product_repository
        self._promotions = promotion_repository

    def compare(
        self,
        *,
        product_ids: Iterable[int] = (),
        references: Iterable[str] = (),
        last_product_ids: Iterable[int] = (),
    ) -> ProductComparisonResult:
        ids = list(product_ids)
        refs = [reference.strip() for reference in references if reference.strip()]
        if not ids and not refs:
            ids = list(last_product_ids)

        products: list[Product] = []
        unresolved: list[str] = []
        ambiguous: dict[str, list[int]] = {}
        for product_id in ids:
            product = self._products.get_by_id(product_id)
            if product is None:
                unresolved.append(str(product_id))
            else:
                products.append(product)
        for reference in refs:
            matches = self._products.find_by_name(reference)
            if not matches:
                unresolved.append(reference)
            elif len(matches) > 1:
                ambiguous[reference] = [product.id for product in matches]
            else:
                products.append(matches[0])

        unique_products = list({product.id: product for product in products}.values())
        if ambiguous:
            return ProductComparisonResult(
                status=ToolStatus.AMBIGUOUS,
                products=[ProductRead.model_validate(item) for item in unique_products],
                unresolved_references=unresolved,
                ambiguous_references=ambiguous,
            )
        if unresolved or len(unique_products) < 2:
            return ProductComparisonResult(
                status=ToolStatus.NOT_FOUND,
                products=[ProductRead.model_validate(item) for item in unique_products],
                unresolved_references=unresolved,
                missing_information=["At least two distinct resolvable products are required."],
            )

        missing: list[str] = []
        rows = [
            self._row("name", unique_products, lambda item: item.name),
            self._row("brand", unique_products, lambda item: item.brand),
            self._row("category", unique_products, lambda item: item.category),
            self._row("price", unique_products, self._price),
            self._row("availability", unique_products, self._availability),
        ]
        for key in COMPARISON_SPEC_KEYS:
            row = self._row(key, unique_products, lambda item, key=key: self._spec(item, key))
            rows.append(row)
            for cell in row.values:
                if cell.value == "N/A":
                    missing.append(f"product:{cell.product_id}:{key}")
        if self._promotions is not None:
            rows.append(self._row("active_promotions", unique_products, self._active_promotions))

        return ProductComparisonResult(
            status=ToolStatus.SUCCESS,
            products=[ProductRead.model_validate(item) for item in unique_products],
            rows=rows,
            missing_information=missing,
        )

    @staticmethod
    def _row(attribute: str, products: list[Product], getter) -> ComparisonRowResult:
        return ComparisonRowResult(
            attribute=attribute,
            values=[
                ComparisonCell(product_id=product.id, value=getter(product) or "N/A")
                for product in products
            ],
        )

    @staticmethod
    def _price(product: Product) -> str:
        if product.price is None:
            return "N/A"
        return f"{product.price} {product.currency}"

    @staticmethod
    def _availability(product: Product) -> str:
        return {True: "in_stock", False: "out_of_stock", None: "N/A"}[product.in_stock]

    @staticmethod
    def _spec(product: Product, key: str) -> str:
        spec = next((item for item in product.specs if item.key == key), None)
        if spec is None:
            return "N/A"
        value: Decimal | str | None = (
            spec.value_num if spec.value_num is not None else spec.value_text
        )
        if value is None:
            return "N/A"
        rendered = (
            ProductComparisonTool._format_decimal(value)
            if isinstance(value, Decimal)
            else value
        )
        return f"{rendered} {spec.unit}".strip() if spec.unit else str(rendered)

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        return format(value.normalize(), "f")

    def _active_promotions(self, product: Product) -> str:
        if self._promotions is None:
            return "N/A"
        promotions = [
            promotion.title
            for promotion in self._promotions.find_valid(product.category)
            if promotion.product_id is None or promotion.product_id == product.id
        ]
        return "; ".join(promotions) if promotions else "N/A"
