from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_intent_parser
from app.main import app
from app.services.intent_parser import IntentParseResult
from app.services.llm_service import LLMAuthenticationError, LLMRateLimitError, LLMTimeoutError
from tests.intent_helpers import make_plan


class StubParser:
    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome

    def parse(self, _message: str) -> IntentParseResult:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _result(message: str) -> IntentParseResult:
    return IntentParseResult(
        plan=make_plan(message),
        model_used="openai/gpt-oss-20b",
        escalated=False,
        latency_ms=12.5,
        token_usage={"total_tokens": 42},
        routing_reasons=(),
    )


def test_parse_endpoint_returns_structured_plan_without_searching() -> None:
    message = "I need a laptop under 100000 DZD"
    app.dependency_overrides[get_intent_parser] = lambda: StubParser(_result(message))
    try:
        response = TestClient(app).post("/api/intent/parse", json={"message": message})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "product_search"
    assert body["filters"]["max_price"] == "100000"
    assert body["model_used"] == "openai/gpt-oss-20b"
    assert body["escalated"] is False


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (LLMTimeoutError(), 504, "timed out"),
        (LLMRateLimitError(), 503, "rate limited"),
        (LLMAuthenticationError(), 503, "authentication failed"),
    ],
)
def test_parse_endpoint_hides_provider_errors(
    error: Exception, status_code: int, detail: str
) -> None:
    app.dependency_overrides[get_intent_parser] = lambda: StubParser(error)
    try:
        response = TestClient(app).post("/api/intent/parse", json={"message": "hello"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status_code
    assert detail in response.json()["detail"]
    assert "traceback" not in response.text.lower()


def test_parse_endpoint_validates_input_before_dependency_use() -> None:
    app.dependency_overrides[get_intent_parser] = lambda: StubParser(_result("x"))
    try:
        response = TestClient(app).post("/api/intent/parse", json={"message": ""})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
