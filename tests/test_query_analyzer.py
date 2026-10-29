# tests/test_query_analyzer.py
import pytest

from models.query_plan import Comparison, Intent
from services.query_analyzer import QueryAnalyzer, detect_language


@pytest.fixture
def analyzer():
    return QueryAnalyzer(known_brands=("BrandX",))


def specs(plan):
    return [(c.key, c.op, c.value) for c in plan.filters.spec_constraints]


def test_main_example_search(analyzer):
    plan = analyzer.analyze("Find a laptop under 100,000 DZD with at least 16 GB RAM")
    assert plan.intent is Intent.PRODUCT_SEARCH
    assert plan.language == "en"
    assert plan.filters.category == "laptop"
    assert plan.filters.max_price == 100000
    assert specs(plan) == [("ram_gb", Comparison.GTE, 16)]
    assert plan.missing_info == ()


def test_message_is_preserved(analyzer):
    assert analyzer.analyze("Find a laptop").message == "Find a laptop"


@pytest.mark.parametrize("message,expected", [
    ("laptop under 90k", 90000),
    ("laptop below 75000 DA", 75000),
    ("I want a laptop, budget of 120000 DZD", 120000),
    ("laptop at most 100.000 DZD", 100000),
    ("laptop under ١٠٠٠٠٠ DZD", 100000),   # أرقام عربية
])
def test_max_price_variants(analyzer, message, expected):
    assert analyzer.analyze(message).filters.max_price == expected


def test_min_price(analyzer):
    plan = analyzer.analyze("laptop over 80000 DZD")
    assert plan.filters.min_price == 80000
    assert plan.filters.max_price is None


def test_price_range(analyzer):
    plan = analyzer.analyze("laptop between 50,000 and 100,000 DZD")
    assert (plan.filters.min_price, plan.filters.max_price) == (50000, 100000)


def test_spec_amount_is_not_mistaken_for_price(analyzer):
    plan = analyzer.analyze("laptop with 16 GB RAM")
    assert plan.filters.max_price is None and plan.filters.min_price is None
    assert specs(plan) == [("ram_gb", Comparison.GTE, 16)]


def test_small_number_without_currency_is_not_a_price(analyzer):
    assert analyzer.analyze("laptop under 5 stars").filters.max_price is None


def test_storage_in_tb_is_converted_to_gb(analyzer):
    assert specs(analyzer.analyze("laptop with 1 TB SSD")) == [("storage_gb", Comparison.GTE, 1024)]


def test_at_most_and_exact_style_qualifiers(analyzer):
    assert specs(analyzer.analyze("laptop with at most 8 GB RAM")) == [("ram_gb", Comparison.LTE, 8)]
    assert specs(analyzer.analyze("laptop with 8 GB RAM or less")) == [("ram_gb", Comparison.LTE, 8)]
    assert specs(analyzer.analyze("laptop with no more than 8 GB RAM")) == [("ram_gb", Comparison.LTE, 8)]


def test_ram_before_number_form(analyzer):
    assert specs(analyzer.analyze("laptop RAM 32GB")) == [("ram_gb", Comparison.GTE, 32)]


def test_inches_and_category_tv(analyzer):
    plan = analyzer.analyze("TV 55 inch under 90000 DZD")
    assert plan.filters.category == "tv"
    assert specs(plan) == [("screen_inches", Comparison.GTE, 55)]
    assert plan.filters.max_price == 90000


def test_in_stock_and_brand(analyzer):
    plan = analyzer.analyze("BrandX laptop in stock")
    assert plan.filters.in_stock_only is True
    assert plan.filters.brand == "BrandX"


def test_missing_category_is_reported(analyzer):
    plan = analyzer.analyze("I want something under 50000 DZD")
    assert plan.intent is Intent.PRODUCT_SEARCH
    assert plan.missing_info == ("category",)


def test_ambiguous_price_direction_is_reported_not_guessed(analyzer):
    plan = analyzer.analyze("laptop 100000 DZD")
    assert plan.filters.max_price is None and plan.filters.min_price is None
    assert plan.missing_info == ("price_bound",)


@pytest.mark.parametrize("message", [
    "What is the difference between OLED and QLED?",
    "What is RAM?",
    "What is a laptop?",
    "Explain how OLED works",
])
def test_explanation_intent(analyzer, message):
    assert analyzer.analyze(message).intent is Intent.EXPLANATION


def test_what_are_with_constraints_is_a_search(analyzer):
    plan = analyzer.analyze("What are laptops under 100000 DZD")
    assert plan.intent is Intent.PRODUCT_SEARCH


def test_comparison_extracts_refs(analyzer):
    plan = analyzer.analyze("Compare Product A and Product B")
    assert plan.intent is Intent.COMPARISON
    assert plan.product_refs == ("Product A", "Product B")
    assert plan.missing_info == ()


def test_comparison_of_three_and_vs_syntax(analyzer):
    assert analyzer.analyze("Compare Laptop A, Laptop B and Laptop C").product_refs == (
        "Laptop A", "Laptop B", "Laptop C")
    assert analyzer.analyze("Laptop A vs Laptop B").product_refs == ("Laptop A", "Laptop B")


def test_comparison_without_two_products_asks_for_them(analyzer):
    assert analyzer.analyze("Compare").missing_info == ("products_to_compare",)
    assert analyzer.analyze("Compare Laptop A").missing_info == ("products_to_compare",)


def test_promotion_and_recommendation_intents(analyzer):
    promo = analyzer.analyze("Are there any promotions on laptops?")
    assert promo.intent is Intent.PROMOTION_SEARCH and promo.filters.category == "laptop"
    rec = analyzer.analyze("Which laptop should I buy for programming?")
    assert rec.intent is Intent.RECOMMENDATION


def test_unknown_and_empty(analyzer):
    assert analyzer.analyze("hello").intent is Intent.UNKNOWN
    empty = analyzer.analyze("   ")
    assert empty.intent is Intent.UNKNOWN and empty.language == "unknown"


def test_language_detection():
    assert detect_language("أريد لابتوب") == "ar"
    assert detect_language("Quel ordinateur pour moins de 100000 DZD") == "fr"
    assert detect_language("Find a laptop") == "en"
    assert detect_language("12345") == "unknown"


def test_arabic_message_keeps_language_but_is_not_yet_understood(analyzer):
    plan = analyzer.analyze("أريد لابتوب")
    assert plan.language == "ar"
    assert plan.intent is Intent.UNKNOWN   # قيد معروف: الاستخراج حاليًا بالإنجليزية فقط
