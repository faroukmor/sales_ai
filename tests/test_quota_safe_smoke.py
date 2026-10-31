from __future__ import annotations

from typing import Any

import pytest

from app.services.model_router import ModelTier
from scripts.quota_safe_groq_smoke import BudgetedRunnable


class FakeRunnable:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, value: Any) -> Any:
        self.calls += 1
        return value


def test_smoke_budget_is_enforced_at_runnable_invocation() -> None:
    counts = {"total": 0, "fast": 0, "powerful": 0}
    fast_underlying = FakeRunnable()
    powerful_underlying = FakeRunnable()
    fast = BudgetedRunnable(fast_underlying, ModelTier.FAST, counts)
    powerful = BudgetedRunnable(powerful_underlying, ModelTier.POWERFUL, counts)

    assert fast.invoke("fast") == "fast"
    with pytest.raises(RuntimeError, match="fast request budget"):
        fast.invoke("repeat")
    assert powerful.invoke("powerful") == "powerful"
    with pytest.raises(RuntimeError, match="total Groq request budget"):
        powerful.invoke("repeat")

    assert counts == {"total": 2, "fast": 1, "powerful": 1}
    assert fast_underlying.calls == 1
    assert powerful_underlying.calls == 1
