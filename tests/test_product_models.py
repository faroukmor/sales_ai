from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Product, ProductSpec


def test_product_preserves_unknown_values_and_relationships(db_session: Session) -> None:
    product = Product(name="Unknown", category="laptop", price=None, in_stock=None)
    product.specs.append(ProductSpec(key="processor", value_text="Fictional CPU"))
    db_session.add(product)
    db_session.commit()

    assert product.price is None
    assert product.in_stock is None
    assert product.specs[0].product is product


def test_negative_price_is_rejected(db_session: Session) -> None:
    db_session.add(Product(name="Invalid", category="laptop", price=Decimal("-0.01")))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_duplicate_specification_key_is_rejected(db_session: Session) -> None:
    product = Product(name="Duplicate spec", category="tv")
    product.specs = [
        ProductSpec(key="screen_inches", value_num=Decimal("55")),
        ProductSpec(key="screen_inches", value_num=Decimal("65")),
    ]
    db_session.add(product)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_product_delete_cascades_specs(db_session: Session) -> None:
    product = Product(name="Cascade", category="tv")
    product.specs.append(ProductSpec(key="resolution", value_text="4K"))
    db_session.add(product)
    db_session.commit()
    spec_id = product.specs[0].id

    db_session.delete(product)
    db_session.commit()

    assert db_session.get(ProductSpec, spec_id) is None
