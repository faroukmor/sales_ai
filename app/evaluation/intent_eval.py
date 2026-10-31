from __future__ import annotations

import argparse
import json
import os
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.intent_parser import SYSTEM_PROMPT, IntentParser
from app.services.llm_service import LLMService
from app.services.model_router import ModelTier
from app.services.query_validator import QueryValidator


@dataclass
class Metrics:
    cases: int = 0
    valid_outputs: int = 0
    intent_correct: int = 0
    slot_correct: int = 0
    slot_total: int = 0
    price_correct: int = 0
    price_total: int = 0
    clarification_correct: int = 0
    escalations: int = 0
    latency_ms: list[float] | None = None
    total_tokens: int = 0

    def report(self) -> dict[str, int | float]:
        latencies = self.latency_ms or []
        return {
            "cases": self.cases,
            "intent_accuracy": _ratio(self.intent_correct, self.cases),
            "slot_accuracy": _ratio(self.slot_correct, self.slot_total),
            "price_accuracy": _ratio(self.price_correct, self.price_total),
            "clarification_accuracy": _ratio(self.clarification_correct, self.cases),
            "invalid_output_rate": _ratio(self.cases - self.valid_outputs, self.cases),
            "escalation_frequency": _ratio(self.escalations, self.cases),
            "mean_latency_ms": round(statistics.fmean(latencies), 2) if latencies else 0.0,
            "total_tokens": self.total_tokens,
        }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def evaluate(cases: list[dict[str, Any]], mode: str) -> dict[str, int | float]:
    settings = get_settings()
    service = LLMService.from_settings(settings)
    validator = QueryValidator()
    parser = IntentParser(
        service,
        validator=validator,
        allow_powerful_fallback=settings.groq_allow_powerful_fallback,
    )
    metrics = Metrics(latency_ms=[])

    for case in cases:
        metrics.cases += 1
        try:
            if mode == "routed":
                result = parser.parse(case["message"])
                plan = result.plan
                metrics.escalations += int(result.escalated)
                latency = result.latency_ms
                usage = result.token_usage
            else:
                tier = ModelTier(mode)
                invocation = service.invoke(tier, SYSTEM_PROMPT, case["message"])
                plan = validator.validate_plan(invocation.plan, case["message"])
                latency = invocation.latency_ms
                usage = invocation.token_usage
        except Exception as error:  # A failed case is data, not an evaluation crash.
            print(json.dumps({"case": case["id"], "error": error.__class__.__name__}))
            continue

        metrics.valid_outputs += 1
        metrics.latency_ms.append(latency)
        metrics.total_tokens += usage.get("total_tokens", usage.get("total_token_count", 0))
        expected = case["expected"]
        metrics.intent_correct += int(plan.intent.value == expected["intent"])
        metrics.clarification_correct += int(
            plan.needs_clarification == expected["needs_clarification"]
        )

        for field in ("language", "category", "brand", "currency", "in_stock_only"):
            metrics.slot_total += 1
            actual = getattr(plan, field)
            actual = actual.value if hasattr(actual, "value") else actual
            metrics.slot_correct += int(actual == expected[field])
        metrics.slot_total += 2
        metrics.slot_correct += int(plan.product_refs == expected["product_refs"])
        actual_specs = [item.model_dump(mode="json") for item in plan.specification_constraints]
        metrics.slot_correct += int(actual_specs == expected["specification_constraints"])

        for field in ("min_price", "max_price"):
            metrics.price_total += 1
            actual_price = getattr(plan, field)
            expected_price = expected[field]
            metrics.price_correct += int(
                (str(actual_price) if actual_price is not None else None)
                == (str(expected_price) if expected_price is not None else None)
            )

    return metrics.report()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate GPT-OSS intent extraction")
    parser.add_argument(
        "--model",
        choices=["fast", "powerful", "routed", "compare"],
        default="compare",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/intent_evaluation.jsonl"),
    )
    args = parser.parse_args()
    if os.getenv("RUN_GROQ_EVALUATION") != "1":
        raise SystemExit("Set RUN_GROQ_EVALUATION=1 to authorize live evaluation calls")

    cases = _load_cases(args.dataset)
    modes = ("fast", "powerful") if args.model == "compare" else (args.model,)
    results = {mode: evaluate(cases, mode) for mode in modes}
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
