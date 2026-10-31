"""Explicit, sequential two-request Groq smoke test. Never imported by the application."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import MutableMapping
from typing import Any

from langchain_groq import ChatGroq

from app.core.config import get_settings
from app.services.intent_parser import SYSTEM_PROMPT
from app.services.llm_service import LLMService
from app.services.model_router import ModelTier
from app.services.query_validator import QueryValidationError, QueryValidator

TOTAL_REQUEST_LIMIT = 2
PER_MODEL_REQUEST_LIMIT = 1
MAX_RESPONSE_TOKENS = 1500


class BudgetedRunnable:
    def __init__(
        self,
        runnable: Any,
        tier: ModelTier,
        counts: MutableMapping[str, int],
    ) -> None:
        self._runnable = runnable
        self._tier = tier
        self._counts = counts

    def invoke(self, value: Any) -> Any:
        if self._counts["total"] >= TOTAL_REQUEST_LIMIT:
            raise RuntimeError("hard total Groq request budget reached")
        if self._counts[self._tier.value] >= PER_MODEL_REQUEST_LIMIT:
            raise RuntimeError(f"hard {self._tier.value} request budget reached")
        # Count at the last local boundary before the provider runnable. The underlying
        # ChatGroq client and LLMService both have retries disabled below.
        self._counts["total"] += 1
        self._counts[self._tier.value] += 1
        return self._runnable.invoke(value)


class BudgetedClient:
    def __init__(
        self,
        client: ChatGroq,
        tier: ModelTier,
        counts: MutableMapping[str, int],
    ) -> None:
        self._client = client
        self._tier = tier
        self._counts = counts

    def with_structured_output(self, schema: dict[str, Any], **kwargs: Any) -> BudgetedRunnable:
        return BudgetedRunnable(
            self._client.with_structured_output(schema, **kwargs),
            self._tier,
            self._counts,
        )


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one quota-safe request per GPT-OSS model")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="required together with CONFIRM_GROQ_SMOKE=YES",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_arguments()
    if not args.execute or os.getenv("CONFIRM_GROQ_SMOKE") != "YES":
        raise SystemExit("Refusing live calls: use --execute with CONFIRM_GROQ_SMOKE=YES")

    settings = get_settings()
    if settings.groq_api_key is None or not settings.groq_api_key.get_secret_value().strip():
        raise SystemExit("GROQ_API_KEY is not configured; zero requests made")

    common: dict[str, Any] = {
        "api_key": settings.groq_api_key,
        "temperature": 0,
        "timeout": settings.groq_timeout_seconds,
        "max_retries": 0,
        "max_tokens": MAX_RESPONSE_TOKENS,
    }
    counts = {"total": 0, "fast": 0, "powerful": 0}
    fast = BudgetedClient(
        ChatGroq(
            model=settings.groq_model_fast,
            reasoning_effort=settings.groq_reasoning_effort_fast,
            **common,
        ),
        ModelTier.FAST,
        counts,
    )
    powerful = BudgetedClient(
        ChatGroq(
            model=settings.groq_model_powerful,
            reasoning_effort=settings.groq_reasoning_effort_powerful,
            **common,
        ),
        ModelTier.POWERFUL,
        counts,
    )
    service = LLMService(
        fast,
        powerful,
        fast_model=settings.groq_model_fast,
        powerful_model=settings.groq_model_powerful,
        max_retries=0,
        sleeper=lambda _seconds: None,
    )
    validator = QueryValidator()
    cases = (
        (ModelTier.FAST, "Find a laptop under 100000 DZD with at least 16GB RAM."),
        (ModelTier.POWERFUL, "نحب PC portable ما يفوتش 10 ملاين ويكون فيه 16 RAM."),
    )
    results: list[dict[str, Any]] = []

    for tier, message in cases:
        try:
            invocation = service.invoke(tier, SYSTEM_PROMPT, message)
        except Exception as error:
            # Stop on every provider failure; this includes rate, quota, billing, timeout,
            # authentication, and availability errors without trying the next model.
            results.append(
                {"tier": tier.value, "outcome": "provider_failed", "error": type(error).__name__}
            )
            break

        result: dict[str, Any] = {
            "tier": tier.value,
            "model_used": invocation.model_used,
            "provider_request_number": counts["total"],
            "latency_ms": round(invocation.latency_ms, 2),
            "token_usage": invocation.token_usage,
        }
        try:
            validator.validate_plan(invocation.plan, message)
        except QueryValidationError as error:
            error.attach_model_metadata(
                model_used=invocation.model_used,
                latency_ms=invocation.latency_ms,
                token_usage=invocation.token_usage,
            )
            result.update(
                {
                    "outcome": "business_validation_failed",
                    "validation": error.safe_diagnostics(),
                }
            )
        else:
            result["outcome"] = "validated"
        results.append(result)

    print(json.dumps({"actual_requests": counts, "results": results}, indent=2))


if __name__ == "__main__":
    main()
