# tests/test_promotion_repository.py
from datetime import date

import pytest

from db.seed_test_data import add_product, add_promotion
from repositories.promotion_repository import PromotionRepository

TODAY = date(2026, 11, 15)


@pytest.fixture
def promos(conn):
    laptop = add_product(conn, "Test Laptop", "laptop")
    add_promotion(conn, "valid-laptops", source="s", category="laptop", starts_at="2026-11-01", ends_at="2026-11-30")
    add_promotion(conn, "expired", source="s", category="laptop", starts_at="2026-10-01", ends_at="2026-11-14")
    add_promotion(conn, "future", source="s", category="laptop", starts_at="2026-11-16", ends_at="2026-12-31")
    add_promotion(conn, "no-end-date", source="s", category="laptop", starts_at="2026-11-01")
    add_promotion(conn, "no-start-date", source="s", category="laptop", ends_at="2026-11-30")
    add_promotion(conn, "valid-tv", source="s", category="tv", starts_at="2026-11-01", ends_at="2026-11-20")
    add_promotion(conn, "valid-on-product", source="s", product_id=laptop, starts_at="2026-11-10", ends_at="2026-11-15")
    conn.commit()
    return PromotionRepository(conn, today=lambda: TODAY)


def titles(promotions):
    return [p.title for p in promotions]


def test_only_verifiably_valid_promotions_are_returned(promos):
    assert titles(promos.find_valid()) == ["valid-on-product", "valid-tv", "valid-laptops"]


def test_expired_future_and_undated_are_excluded(promos):
    result = titles(promos.find_valid())
    for excluded in ("expired", "future", "no-end-date", "no-start-date"):
        assert excluded not in result


def test_boundary_dates_are_inclusive(promos):
    assert "valid-on-product" in titles(promos.find_valid())   # ينتهي اليوم نفسه
    later = PromotionRepository(promos._conn, today=lambda: date(2026, 11, 16))
    assert "valid-on-product" not in titles(later.find_valid())
    assert "future" in titles(later.find_valid())               # يبدأ اليوم نفسه


def test_category_filter_matches_direct_and_via_product(promos):
    assert titles(promos.find_valid(category="laptop")) == ["valid-on-product", "valid-laptops"]
    assert titles(promos.find_valid(category="TV")) == ["valid-tv"]


def test_no_promotions_in_category(promos):
    assert promos.find_valid(category="phone") == []


def test_returned_objects_have_parsed_dates(promos):
    p = promos.find_valid(category="tv")[0]
    assert p.starts_at == date(2026, 11, 1) and p.ends_at == date(2026, 11, 20)
    assert p.source == "s"
