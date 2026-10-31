from __future__ import annotations

import pytest

from app.schemas.query_plan import QuerySpecificationConstraint
from app.services.query_validator import InadequatePlanError, QueryValidator
from tests.intent_helpers import make_plan


@pytest.mark.parametrize(
    ("message", "overrides", "expected"),
    [
        (
            "Find a laptop under 100000 DZD with at least 16GB RAM.",
            {
                "original_message": "Find a laptop under 100000 DZD with at least 16GB RAM",
                "category": "Laptop",
                "currency": "dzd",
                "specification_constraints": [
                    {"key": "RAM_GB", "operator": "gte", "value": 16, "unit": "gb"}
                ],
            },
            ("laptop", "DZD", "ram_gb", "GB"),
        ),
        (
            "Je veux un PC portable avec 16 Go de RAM à moins de 100000 DA.",
            {
                "category": "PC portable",
                "currency": "DA",
                "specification_constraints": [
                    {"key": "ram", "operator": "gte", "value": 16, "unit": "Go"}
                ],
            },
            ("laptop", "DZD", "ram_gb", "GB"),
        ),
        (
            "نحتاج حاسوب محمول أقل من 100 ألف دينار.",
            {"category": "حاسوب محمول", "currency": "دينار"},
            ("laptop", "DZD", None, None),
        ),
        (
            "3tini pc portable b moins de 100000 da.",
            {"category": "pc portable", "currency": "da"},
            ("laptop", "DZD", None, None),
        ),
        (
            "Show me une télévision 55 pouces.",
            {
                "language": "mixed",
                "category": "Télévision",
                "currency": None,
                "max_price": None,
                "specification_constraints": [
                    {"key": "screen_size", "operator": "eq", "value": 55, "unit": "pouces"}
                ],
            },
            ("tv", None, "screen_inches", "inch"),
        ),
    ],
)
def test_realistic_multilingual_model_variants_are_canonicalized(
    message: str,
    overrides: dict[str, object],
    expected: tuple[str, str | None, str | None, str | None],
) -> None:
    plan = make_plan(message, **overrides)
    validated = QueryValidator().validate_plan(plan, message)
    category, currency, key, unit = expected

    assert validated.original_message == message
    assert validated.category == category
    assert validated.currency == currency
    if key is None:
        assert validated.specification_constraints == []
    else:
        assert validated.specification_constraints[0].key == key
        assert validated.specification_constraints[0].unit == unit


@pytest.mark.parametrize(
    "plan",
    [
        make_plan(
            "Compare TEST-LAPTOP-01 and TEST-LAPTOP-02.",
            intent="comparison",
            category=None,
            max_price=None,
            currency=None,
            product_refs=["TEST-LAPTOP-01", "TEST-LAPTOP-02"],
        ),
        make_plan(
            "Recommend a laptop for programming.",
            intent="recommendation",
            max_price=None,
            currency=None,
            needs_clarification=True,
            missing_info=["budget", "workload"],
            clarification_question="What budget and programming workload do you have?",
        ),
        make_plan(
            "وريني les promotions تاع TV.",
            intent="promotion_search",
            language="mixed",
            category="TV",
            max_price=None,
            currency=None,
        ),
        make_plan(
            "نحب PC بحوالي عشرة ملاين ولا يمكن أكثر، ما نيش متأكد.",
            language="dz",
            max_price=None,
            currency=None,
            needs_clarification=True,
            missing_info=["budget"],
            clarification_question="واش هو الحد الأقصى بالـ DZD؟",
        ),
    ],
)
def test_comparison_recommendation_promotion_and_ambiguity_plans_are_valid(plan) -> None:
    assert QueryValidator().validate_plan(plan, plan.original_message)


def test_unsupported_spec_reports_safe_field_diagnostics() -> None:
    message = "Find a laptop with a fast processor"
    plan = make_plan(
        message,
        max_price=None,
        currency=None,
        specification_constraints=[
            QuerySpecificationConstraint(
                key="processor_speed", operator="gte", value=4, unit="GHz"
            )
        ],
    )

    with pytest.raises(InadequatePlanError) as error:
        QueryValidator().validate_plan(plan, message)

    assert error.value.issue.code == "spec_key_unsupported"
    assert error.value.issue.field_path == "specification_constraints.0.key"
    assert "processor_speed" not in str(error.value.safe_diagnostics())
