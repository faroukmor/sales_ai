import json
from pathlib import Path


def test_evaluation_dataset_has_required_multilingual_coverage() -> None:
    path = Path("data/intent_evaluation.jsonl")
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    assert len(cases) >= 40
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["expected"]["language"] for case in cases} >= {
        "ar",
        "dz",
        "fr",
        "en",
        "mixed",
        "unknown",
    }
    required = {
        "intent",
        "language",
        "category",
        "brand",
        "min_price",
        "max_price",
        "currency",
        "in_stock_only",
        "specification_constraints",
        "product_refs",
        "needs_clarification",
    }
    assert all(required <= set(case["expected"]) for case in cases)
