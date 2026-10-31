import pytest

from app.services.model_router import ModelRouter, ModelTier


@pytest.mark.parametrize(
    "message",
    [
        "Find a laptop under 100000 DZD with 16GB RAM.",
        "Je veux un PC portable à moins de 100000 DA.",
        "نحتاج حاسوب محمول أقل من 100 ألف دينار.",
    ],
)
def test_simple_requests_use_fast_model(message: str) -> None:
    assert ModelRouter().choose(message).tier is ModelTier.FAST


@pytest.mark.parametrize(
    ("message", "reason"),
    [
        ("Compare this television with the second one", "ambiguous_product_references"),
        ("3tini pc مليح mais pas cher pour gaming", "highly_colloquial"),
        ("Recommend a laptop but compare it with TEST-LAPTOP-01", "multiple_intentions"),
        (
            "Find a laptop under 100000 DZD with 16GB RAM and 512GB storage",
            "multiple_constraints",
        ),
    ],
)
def test_complex_requests_use_powerful_model(message: str, reason: str) -> None:
    decision = ModelRouter().choose(message)
    assert decision.tier is ModelTier.POWERFUL
    assert reason in decision.reasons


def test_escalation_is_bounded_to_fast_model() -> None:
    router = ModelRouter()
    assert router.can_escalate(
        ModelTier.FAST, fallback_enabled=True, recoverable_failure=True
    )
    assert not router.can_escalate(
        ModelTier.POWERFUL, fallback_enabled=True, recoverable_failure=True
    )
