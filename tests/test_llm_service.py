from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest

from app.services.llm_service import (
    InvalidStructuredResponseError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMService,
    LLMTimeoutError,
)
from app.services.model_router import ModelTier
from tests.intent_helpers import make_plan


class FakeRaw:
    usage_metadata = {"input_tokens": 12, "output_tokens": 8, "total_tokens": 20}
    response_metadata: dict[str, Any] = {}


class FakeRunnable:
    def __init__(self, outcomes: Iterable[Any]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def invoke(self, _messages: Any) -> Any:
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, runnable: FakeRunnable) -> None:
        self.runnable = runnable
        self.structured_kwargs: list[dict[str, Any]] = []

    def with_structured_output(self, _schema: dict[str, Any], **kwargs: Any) -> FakeRunnable:
        self.structured_kwargs.append(kwargs)
        return self.runnable


class RateLimitError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class APITimeoutError(Exception):
    pass


def _service(outcomes: list[Any], retries: int = 2) -> tuple[LLMService, FakeClient]:
    client = FakeClient(FakeRunnable(outcomes))
    service = LLMService(
        client,
        client,
        fast_model="fast-model",
        powerful_model="powerful-model",
        max_retries=retries,
        sleeper=lambda _seconds: None,
    )
    return service, client


def test_structured_output_configuration_and_usage_metadata() -> None:
    message = "find laptop"
    service, client = _service(
        [{"parsed": make_plan(message).model_dump(), "raw": FakeRaw(), "parsing_error": None}]
    )

    result = service.invoke(ModelTier.FAST, "system", message)

    assert result.model_used == "fast-model"
    assert result.token_usage["total_tokens"] == 20
    assert client.structured_kwargs == [
        {"method": "json_schema", "include_raw": True, "strict": True}
    ]


def test_rate_limit_stops_after_bounded_retries() -> None:
    service, client = _service([RateLimitError(), RateLimitError(), RateLimitError()])
    with pytest.raises(LLMRateLimitError):
        service.invoke(ModelTier.FAST, "system", "message")
    assert client.runnable.calls == 3


def test_timeout_can_recover_within_retry_limit() -> None:
    message = "find laptop"
    response = {"parsed": make_plan(message), "raw": FakeRaw(), "parsing_error": None}
    service, client = _service([APITimeoutError(), response], retries=1)
    assert service.invoke(ModelTier.FAST, "system", message).plan.category == "laptop"
    assert client.runnable.calls == 2


def test_timeout_exhaustion_is_explicit() -> None:
    service, _client = _service([APITimeoutError()], retries=0)
    with pytest.raises(LLMTimeoutError):
        service.invoke(ModelTier.FAST, "system", "message")


def test_authentication_failure_is_never_retried() -> None:
    service, client = _service([AuthenticationError(), make_plan("message")])
    with pytest.raises(LLMAuthenticationError):
        service.invoke(ModelTier.FAST, "system", "message")
    assert client.runnable.calls == 1


def test_invalid_structured_response_is_not_retried() -> None:
    service, client = _service([{"parsed": None, "raw": FakeRaw(), "parsing_error": None}])
    with pytest.raises(InvalidStructuredResponseError):
        service.invoke(ModelTier.FAST, "system", "message")
    assert client.runnable.calls == 1
