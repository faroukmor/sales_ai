# tests/test_product_repository.py
import pytest

from models.query_plan import Comparison, ProductFilters, SpecConstraint


def names(products):
    return [p.name for p in products]


def ram(op, value):
    return SpecConstraint("ram_gb", op, value)


# ---------- الفلاتر الأساسية ----------

def test_category_filter_returns_only_that_category(repo):
    result = repo.search(ProductFilters(category="tv"))
    assert names(result) == ["Test TV A"]


def test_category_and_brand_are_case_insensitive(repo):
    result = repo.search(ProductFilters(category="LAPTOP", brand="brandx"))
    assert names(result) == ["Test Laptop C", "Test Laptop A"]


def test_max_price_excludes_expensive_and_unknown_price(repo):
    result = repo.search(ProductFilters(category="laptop", max_price=100000))
    assert names(result) == ["Test Laptop C", "Test Laptop E", "Test Laptop A"]


def test_price_range(repo):
    result = repo.search(
        ProductFilters(category="laptop", min_price=90000, max_price=100000)
    )
    assert names(result) == ["Test Laptop E", "Test Laptop A"]


def test_in_stock_only_excludes_out_of_stock_and_unknown(repo):
    result = repo.search(ProductFilters(category="laptop", in_stock_only=True))
    assert names(result) == ["Test Laptop E", "Test Laptop A", "Test Laptop B"]


# ---------- فلترة المواصفات ----------

def test_spec_gte(repo):
    f = ProductFilters(category="laptop", spec_constraints=(ram(Comparison.GTE, 16),))
    assert names(repo.search(f)) == ["Test Laptop A", "Test Laptop B", "Test Laptop D"]


def test_spec_lte(repo):
    f = ProductFilters(category="laptop", spec_constraints=(ram(Comparison.LTE, 8),))
    assert names(repo.search(f)) == ["Test Laptop C"]


def test_spec_eq(repo):
    f = ProductFilters(category="laptop", spec_constraints=(ram(Comparison.EQ, 16),))
    assert names(repo.search(f)) == ["Test Laptop A", "Test Laptop B"]


def test_product_without_the_spec_never_matches(repo):
    # حتى شرط "ram >= 0" لا يطابق المنتج الذي لا تُسجَّل له مواصفة ram_gb
    f = ProductFilters(category="laptop", spec_constraints=(ram(Comparison.GTE, 0),))
    assert "Test Laptop E" not in names(repo.search(f))


def test_two_spec_constraints_must_both_hold(repo):
    f = ProductFilters(
        category="laptop",
        spec_constraints=(
            ram(Comparison.GTE, 16),
            SpecConstraint("storage_gb", Comparison.GTE, 1024),
        ),
    )
    assert names(repo.search(f)) == ["Test Laptop B"]


def test_example_one_laptop_under_100k_with_16gb(repo):
    f = ProductFilters(
        category="laptop", max_price=100000,
        spec_constraints=(ram(Comparison.GTE, 16),),
    )
    assert names(repo.search(f)) == ["Test Laptop A"]


def test_unknown_operator_is_rejected_before_reaching_sql(repo):
    bad = SpecConstraint("ram_gb", "> 0; DROP TABLE products; --", 16)
    with pytest.raises(ValueError):
        repo.search(ProductFilters(spec_constraints=(bad,)))


# ---------- النتائج الفارغة والترتيب والحدود ----------

def test_no_match_returns_empty_list(repo):
    assert repo.search(ProductFilters(category="laptop", max_price=1000)) == []


def test_results_sorted_by_price_with_unknown_price_last(repo):
    result = repo.search(ProductFilters(category="laptop"))
    assert names(result)[-1] == "Test Laptop D"
    prices = [p.price for p in result[:-1]]
    assert prices == sorted(prices)


def test_limit_is_applied(repo):
    assert len(repo.search(ProductFilters(category="laptop"), limit=2)) == 2


def test_invalid_limit_raises(repo):
    with pytest.raises(ValueError):
        repo.search(ProductFilters(), limit=0)


# ---------- صحة البيانات المرجَعة ----------

def test_specs_are_loaded_with_values_and_units(repo):
    product = repo.search(ProductFilters(category="laptop", max_price=95000, brand="BrandX"))[-1]
    assert product.name == "Test Laptop A"
    assert product.get_spec("ram_gb").value_num == 16.0
    assert product.get_spec("ram_gb").unit == "GB"


def test_text_spec_keeps_text_and_has_no_number(repo):
    tv = repo.search(ProductFilters(category="tv"))[0]
    assert tv.get_spec("panel_type").value_text == "OLED"
    assert tv.get_spec("panel_type").value_num is None


def test_unknown_values_stay_none(repo):
    d = next(p for p in repo.search(ProductFilters(category="laptop")) if p.name == "Test Laptop D")
    assert d.price is None
    assert d.in_stock is None
    assert d.is_test_data is True


def test_product_without_specs_has_empty_specs(repo):
    e = next(p for p in repo.search(ProductFilters(category="laptop")) if p.name == "Test Laptop E")
    assert e.specs == {}
    assert e.get_spec("ram_gb") is None


# ---------- get_by_id ----------

def test_get_by_id_returns_product_with_specs(repo):
    product = repo.get_by_id(1)
    assert product.name == "Test Laptop A"
    assert product.get_spec("storage_gb").value_num == 512.0


def test_get_by_id_missing_returns_none(repo):
    assert repo.get_by_id(9999) is None


# ---------- الأمان ----------

def test_sql_injection_in_values_is_treated_as_data(repo, conn):
    evil = "laptop' OR '1'='1"
    assert repo.search(ProductFilters(category=evil)) == []
    evil_key = SpecConstraint("ram_gb' OR '1'='1", Comparison.GTE, 0)
    assert repo.search(ProductFilters(spec_constraints=(evil_key,))) == []
    assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 6


# ---------- find_by_name و list_brands ----------

def test_find_by_name_exact_match_wins_over_partial(repo):
    assert names(repo.find_by_name("test laptop a")) == ["Test Laptop A"]


def test_find_by_name_partial_match(repo):
    assert names(repo.find_by_name("TV A")) == ["Test TV A"]


def test_find_by_name_ambiguous_returns_several(repo):
    assert len(repo.find_by_name("Test Laptop")) == 5


def test_find_by_name_unknown_or_blank_returns_empty(repo):
    assert repo.find_by_name("Nonexistent") == []
    assert repo.find_by_name("   ") == []


def test_find_by_name_treats_wildcards_as_text(repo):
    assert repo.find_by_name("%") == []
    assert repo.find_by_name("Test_Laptop A") == []


def test_list_brands_is_distinct_sorted_and_skips_null(repo):
    assert repo.list_brands() == ["BrandX", "BrandY"]
