from decimal import Decimal

from app.db.database import SessionLocal
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_repository import PromotionRepository
from app.schemas.product_filters import ProductFilters, SpecConstraint


def _price(product_price: Decimal | None, currency: str) -> str:
    return f"{product_price:.2f} {currency}" if product_price is not None else "price unknown"


def main() -> None:
    with SessionLocal() as session:
        products = ProductRepository(session)
        promotions = PromotionRepository(session)

        print("=== PRODUCT SEARCH ===\n")
        print("Laptops under 100000 DZD:")
        affordable = products.search(ProductFilters(category="laptop", max_price=Decimal("100000")))
        for product in affordable:
            print(f"- {product.name} | {_price(product.price, product.currency)}")

        print("\nLaptops with at least 16 GB RAM:")
        capable = products.search(
            ProductFilters(
                category="laptop",
                spec_constraints=[SpecConstraint(key="ram_gb", operator="gte", value=16)],
            )
        )
        for product in capable:
            print(f"- {product.name} | {_price(product.price, product.currency)}")

        if affordable:
            product = products.get_by_id(affordable[0].id)
            print(f"\nProduct by ID: {product.name if product else 'not found'}")

        matches = products.find_by_name("TEST-LAPTOP-01")
        print(f"Product by name: {matches[0].name if matches else 'not found'}")

        print("\n=== VALID PROMOTIONS ===\n")
        print("Active offers:")
        active = promotions.find_valid()
        if not active:
            print("- none")
        for promotion in active:
            print(f"- {promotion.title}")


if __name__ == "__main__":
    main()
