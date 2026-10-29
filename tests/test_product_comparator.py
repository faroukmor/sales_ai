# tests/test_product_comparator.py
import pytest

from models.product import Product, Spec
from services.product_comparator import ProductComparator


def product(pid, name, price=None, **specs):
    return Product(
        id=pid, name=name, category="laptop", currency="DZD", price=price,
        specs={k: Spec(k, value_text=str(v[0]), value_num=float(v[0]), unit=v[1]) for k, v in specs.items()},
    )


def row(result, key):
    return next(r for r in result.rows if r.key == key)


def test_needs_two_products():
    with pytest.raises(ValueError):
        ProductComparator().compare([product(1, "A")])


def test_price_and_spec_rows_with_differences():
    a = product(1, "A", 95000, ram_gb=(16, "GB"))
    b = product(2, "B", 120000, ram_gb=(32, "GB"))
    result = ProductComparator().compare([a, b])
    assert result.product_names == ("A", "B")
    assert row(result, "price").values == ("95000 DZD", "120000 DZD")
    assert row(result, "ram_gb").values == ("16 GB", "32 GB")
    assert row(result, "ram_gb").differs is True


def test_equal_values_do_not_differ():
    a = product(1, "A", 1, ram_gb=(16, "GB"))
    b = product(2, "B", 2, ram_gb=(16, "GB"))
    assert row(ProductComparator().compare([a, b]), "ram_gb").differs is False


def test_missing_values_stay_none_and_are_flagged():
    a = product(1, "A", None, ram_gb=(16, "GB"))
    b = product(2, "B", 90000)   # بلا مواصفات
    result = ProductComparator().compare([a, b])
    assert row(result, "price").values == (None, "90000 DZD")
    assert row(result, "ram_gb").values == ("16 GB", None)
    assert row(result, "ram_gb").has_missing is True
    assert row(result, "ram_gb").differs is False   # قيمة واحدة مسجَّلة لا تكفي للحكم بالاختلاف


def test_spec_keys_are_the_union_in_sorted_order():
    a = product(1, "A", 1, ram_gb=(8, "GB"))
    b = product(2, "B", 1, storage_gb=(256, "GB"))
    keys = [r.key for r in ProductComparator().compare([a, b]).rows]
    assert keys == ["price", "ram_gb", "storage_gb"]


def test_large_price_is_not_in_scientific_notation():
    a, b = product(1, "A", 1500000), product(2, "B", 2)
    assert row(ProductComparator().compare([a, b]), "price").values[0] == "1500000 DZD"


def test_three_products():
    result = ProductComparator().compare([product(i, f"P{i}", i * 1000) for i in (1, 2, 3)])
    assert len(row(result, "price").values) == 3
