from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import groq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.query_plan import QueryPlan, groq_query_plan_schema
from app.services.model_router import ModelTier

logger = logging.getLogger(__name__)


class LLMServiceError(RuntimeError):
    pass


class LLMConfigurationError(LLMServiceError):
    pass


class LLMAuthenticationError(LLMServiceError):
    pass


class LLMRateLimitError(LLMServiceError):
    pass


class LLMTimeoutError(LLMServiceError):
    pass


class LLMUnavailableError(LLMServiceError):
    pass


class InvalidStructuredResponseError(LLMServiceError):
    pass


class StructuredClient(Protocol):
    def with_structured_output(self, schema: dict[str, Any], **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class ModelInvocation:
    plan: QueryPlan
    model_used: str
    latency_ms: float
    token_usage: dict[str, int]


class LLMService:
    def __init__(
        self,
        fast_client: StructuredClient,
        powerful_client: StructuredClient,
        *,
        fast_model: str,
        powerful_model: str,
        max_retries: int,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._clients = {
            ModelTier.FAST: fast_client,
            ModelTier.POWERFUL: powerful_client,
        }
        self._models = {
            ModelTier.FAST: fast_model,
            ModelTier.POWERFUL: powerful_model,
        }
        self._max_retries = max_retries
        self._sleeper = sleeper
        self._clock = clock

    @classmethod
    def from_settings(cls, settings: Settings) -> LLMService:
        api_key = settings.groq_api_key
        if api_key is None or not api_key.get_secret_value().strip():
            raise LLMConfigurationError("Groq API key is not configured")

        common: dict[str, Any] = {
            "api_key": api_key,
            "temperature": 0,
            "timeout": settings.groq_timeout_seconds,
            # Retry in this service only, preventing nested retry multiplication.
            "max_retries": 0,
        }
        fast = ChatGroq(
            model=settings.groq_model_fast,
            reasoning_effort=settings.groq_reasoning_effort_fast,
            **common,
        )
        powerful = ChatGroq(
            model=settings.groq_model_powerful,
            reasoning_effort=settings.groq_reasoning_effort_powerful,
            **common,
        )
        return cls(
            fast,
            powerful,
            fast_model=settings.groq_model_fast,
            powerful_model=settings.groq_model_powerful,
            max_retries=settings.groq_max_retries,
        )

    def invoke(self, tier: ModelTier, system_prompt: str, message: str) -> ModelInvocation:
        client = self._clients[tier]
        model_name = self._models[tier]
        started = self._clock()
        for attempt in range(self._max_retries + 1):
            try:
                runnable = client.with_structured_output(
                    groq_query_plan_schema(),
                    method="json_schema",
                    include_raw=True,
                    strict=True,
                )
                response = runnable.invoke(
                    [SystemMessage(content=system_prompt), HumanMessage(content=message)]
                )
                plan, usage = self._parse_response(response)
                return ModelInvocation(
                    plan=plan,
                    model_used=model_name,
                    latency_ms=(self._clock() - started) * 1000,
                    token_usage=usage,
                )
            except (ValidationError, TypeError, KeyError) as error:
                raise InvalidStructuredResponseError("invalid structured model response") from error
            except InvalidStructuredResponseError:
                raise
            except Exception as error:
                category = self._classify_error(error)
                if category is LLMAuthenticationError:
                    raise category("Groq authentication failed") from error
                retryable = category in {LLMRateLimitError, LLMTimeoutError, LLMUnavailableError}
                if not retryable or attempt >= self._max_retries:
                    raise category(self._public_error_message(category)) from error
                logger.warning(
                    "Retrying Groq request",
                    extra={"model_tier": tier.value, "attempt": attempt + 1},
                )
                self._sleeper(min(0.25 * (2**attempt), 2.0))

        raise LLMServiceError("unreachable retry state")

    @staticmethod
    def _parse_response(response: Any) -> tuple[QueryPlan, dict[str, int]]:
        if isinstance(response, QueryPlan):
            return response, {}
        if not isinstance(response, Mapping):
            raise TypeError("structured response must be a mapping")
        parsing_error = response.get("parsing_error")
        if parsing_error is not None:
            raise InvalidStructuredResponseError("model response failed structured parsing")
        parsed = response.get("parsed")
        if parsed is None:
            raise InvalidStructuredResponseError("model response did not contain parsed data")
        plan = parsed if isinstance(parsed, QueryPlan) else QueryPlan.model_validate(parsed)
        return plan, LLMService._extract_usage(response.get("raw"))

    @staticmethod
    def _extract_usage(raw: Any) -> dict[str, int]:
        candidates = [
            getattr(raw, "usage_metadata", None),
            getattr(raw, "response_metadata", {}).get("token_usage")
            if raw is not None
            else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, Mapping):
                usage = {
                    str(key): int(value)
                    for key, value in candidate.items()
                    if isinstance(value, int) and not isinstance(value, bool)
                }
                if usage:
                    return usage
        return {}

    @staticmethod
    def _classify_error(error: Exception) -> type[LLMServiceError]:
        if isinstance(error, groq.AuthenticationError) or error.__class__.__name__ in {
            "AuthenticationError",
            "PermissionDeniedError",
        }:
            return LLMAuthenticationError
        if isinstance(error, groq.RateLimitError) or error.__class__.__name__ == "RateLimitError":
            return LLMRateLimitError
        if isinstance(error, (groq.APITimeoutError, TimeoutError)) or error.__class__.__name__ in {
            "APITimeoutError",
            "ReadTimeout",
        }:
            return LLMTimeoutError
        if isinstance(error, groq.APIStatusError) and error.status_code >= 500:
            return LLMUnavailableError
        if error.__class__.__name__ in {"InternalServerError", "ServiceUnavailableError"}:
            return LLMUnavailableError
        return LLMServiceError

    @staticmethod
    def _public_error_message(category: type[LLMServiceError]) -> str:
        return {
            LLMRateLimitError: "Groq rate limit remained unavailable after bounded retries",
            LLMTimeoutError: "Groq request timed out after bounded retries",
            LLMUnavailableError: "Groq service remained unavailable after bounded retries",
            LLMServiceError: "Groq request failed",
        }[category]
