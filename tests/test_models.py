# tests/test_models.py
import dataclasses
import json

import pytest

from models.chat_response import ChatResponse, Status
from models.product import Product, Spec
from models.query_plan import (
    Comparison, Intent, ProductFilters, QueryPlan, SpecConstraint,
)


def make_product(**overrides):
    base = dict(id=1, name="Test Laptop A", category="laptop", currency="DZD")
    base.update(overrides)
    return Product(**base)


def test_product_is_immutable():
    p = make_product(price=95000.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.price = 1.0


def test_get_spec_returns_none_when_missing():
    assert make_product().get_spec("ram_gb") is None


def test_get_spec_returns_recorded_spec():
    spec = Spec("ram_gb", value_text="16", value_num=16.0, unit="GB")
    p = make_product(specs={"ram_gb": spec})
    assert p.get_spec("ram_gb").value_num == 16.0


def test_unknown_price_is_none_not_zero():
    assert make_product().price is None


def test_products_do_not_share_default_specs():
    a, b = make_product(id=1), make_product(id=2)
    assert a.specs is not b.specs


def test_query_plan_defaults_are_explicit_unknowns():
    plan = QueryPlan(message="hello")
    assert plan.intent is Intent.UNKNOWN
    assert plan.language == "unknown"
    assert plan.missing_info == ()
    assert plan.filters.category is None


def test_spec_constraint_in_filters():
    c = SpecConstraint("ram_gb", Comparison.GTE, 16)
    f = ProductFilters(category="laptop", max_price=100000, spec_constraints=(c,))
    assert f.spec_constraints[0].op is Comparison.GTE


def test_chat_response_defaults_have_no_products_or_sources():
    r = ChatResponse(answer="x", intent=Intent.UNKNOWN, status=Status.OK)
    assert r.products == ()
    assert r.sources == ()


def test_status_serializes_as_plain_string():
    assert json.dumps(Status.NO_RESULTS) == '"no_results"'


def test_chat_response_new_fields_default_to_empty():
    r = ChatResponse(answer="x", intent=Intent.UNKNOWN, status=Status.OK)
    assert r.promotions == ()
    assert r.comparison is None


def test_not_supported_status_exists():
    assert Status.NOT_SUPPORTED.value == "not_supported"
