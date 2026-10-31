from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.schemas.query_plan import Intent, QueryPlan, QuerySpecificationConstraint


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    field_path: str
    reason: str
    expected: str | None = None

    def safe_dict(self) -> dict[str, str]:
        details = {
            "code": self.code,
            "field_path": self.field_path,
            "reason": self.reason,
        }
        if self.expected is not None:
            details["expected"] = self.expected
        return details


class QueryValidationError(ValueError):
    """Safe validation failure with optional unlogged diagnostic context."""

    recoverable_with_powerful_model = False

    def __init__(
        self,
        code: str,
        field_path: str,
        reason: str,
        expected: str | None = None,
        *,
        rejected_plan: QueryPlan | None = None,
    ) -> None:
        self.issue = ValidationIssue(code, field_path, reason, expected)
        self.rejected_plan = rejected_plan
        self.model_used: str | None = None
        self.latency_ms: float | None = None
        self.token_usage: dict[str, int] = {}
        super().__init__(f"{code} at {field_path}: {reason}")

    def attach_model_metadata(
        self,
        *,
        model_used: str,
        latency_ms: float,
        token_usage: Mapping[str, int],
    ) -> QueryValidationError:
        self.model_used = model_used
        self.latency_ms = latency_ms
        self.token_usage = dict(token_usage)
        return self

    def safe_diagnostics(self) -> dict[str, Any]:
        details: dict[str, Any] = self.issue.safe_dict()
        if self.model_used is not None:
            details["model_used"] = self.model_used
        if self.latency_ms is not None:
            details["latency_ms"] = round(self.latency_ms, 2)
        if self.token_usage:
            details["token_usage"] = self.token_usage
        return details


class UnsafeInputError(QueryValidationError):
    pass


class InadequatePlanError(QueryValidationError):
    recoverable_with_powerful_model = True


class QueryValidator:
    MAX_MESSAGE_LENGTH = 2000
    MAX_CONSTRAINTS = 10
    MAX_PRODUCT_REFS = 10
    DEFAULT_CATEGORIES = frozenset({"laptop", "tv", "smartphone"})
    CATEGORY_ALIASES = {
        "laptop": "laptop",
        "pc portable": "laptop",
        "ordinateur portable": "laptop",
        "حاسوب محمول": "laptop",
        "كمبيوتر محمول": "laptop",
        "tv": "tv",
        "television": "tv",
        "télévision": "tv",
        "televiseur": "tv",
        "téléviseur": "tv",
        "تلفاز": "tv",
        "smartphone": "smartphone",
        "phone": "smartphone",
        "telephone": "smartphone",
        "téléphone": "smartphone",
        "هاتف": "smartphone",
        "هاتف ذكي": "smartphone",
    }
    CURRENCY_ALIASES = {
        "DZD": "DZD",
        "DA": "DZD",
        "DINAR": "DZD",
        "DINARS": "DZD",
        "DINAR ALGERIEN": "DZD",
        "DINAR ALGÉRIEN": "DZD",
        "دينار": "DZD",
        "دج": "DZD",
    }
    SPEC_KEY_ALIASES = {
        "ram": "ram_gb",
        "ram_gb": "ram_gb",
        "memory_gb": "ram_gb",
        "storage": "storage_gb",
        "storage_gb": "storage_gb",
        "screen_size": "screen_inches",
        "screen_size_inches": "screen_inches",
        "screen_inches": "screen_inches",
        "refresh_rate": "refresh_rate_hz",
        "refresh_rate_hz": "refresh_rate_hz",
    }
    SPEC_UNITS = {
        "ram_gb": {"gb": "GB", "go": "GB"},
        "storage_gb": {"gb": "GB", "go": "GB"},
        "screen_inches": {"inch": "inch", "inches": "inch", "pouce": "inch", "pouces": "inch"},
        "refresh_rate_hz": {"hz": "Hz"},
    }
    _safe_ref = re.compile(r"^[^\x00-\x1f\x7f]{1,120}$")
    _injection = re.compile(
        r"(ignore|disregard|override)\s+(all\s+)?(previous|prior|system)|"
        r"reveal\s+(the\s+)?(system|developer)\s+prompt|"
        r"prompt\s+injection|"
        r"تجاهل\s+(كل\s+)?التعليمات|"
        r"ignore\s+les\s+instructions",
        re.IGNORECASE,
    )

    def __init__(self, supported_categories: Collection[str] | None = None) -> None:
        categories = supported_categories or self.DEFAULT_CATEGORIES
        self._supported_categories = frozenset(item.casefold() for item in categories)

    def validate_input(self, message: str) -> str:
        normalized = message.strip()
        if not normalized:
            raise QueryValidationError(
                "message_empty", "message", "message must not be empty", "1-2000 characters"
            )
        if len(normalized) > self.MAX_MESSAGE_LENGTH:
            raise QueryValidationError(
                "message_too_long",
                "message",
                "message exceeds maximum length",
                f"at most {self.MAX_MESSAGE_LENGTH} characters",
            )
        if self._injection.search(normalized):
            raise UnsafeInputError(
                "prompt_override_attempt",
                "message",
                "instruction-override content is not accepted",
            )
        return normalized

    def validate_plan(self, plan: QueryPlan, original_message: str) -> QueryPlan:
        # The trusted request owns this field. An LLM echo is not authoritative and should
        # never cause a second provider call merely because punctuation or spacing changed.
        updates: dict[str, object] = {"original_message": original_message}

        if plan.min_price is not None and plan.min_price < Decimal(0):
            self._reject(
                plan,
                "price_negative",
                "min_price",
                "minimum price cannot be negative",
                "null or a non-negative decimal",
            )
        if plan.max_price is not None and plan.max_price < Decimal(0):
            self._reject(
                plan,
                "price_negative",
                "max_price",
                "maximum price cannot be negative",
                "null or a non-negative decimal",
            )
        if plan.min_price is not None and plan.max_price is not None:
            if plan.min_price > plan.max_price:
                self._reject(
                    plan,
                    "price_range_invalid",
                    "min_price,max_price",
                    "minimum price cannot exceed maximum price",
                    "min_price <= max_price",
                )

        if plan.category is not None:
            category_input = self._normalized_text(plan.category)
            category = self.CATEGORY_ALIASES.get(category_input, category_input)
            if category not in self._supported_categories:
                self._reject(
                    plan,
                    "category_unsupported",
                    "category",
                    "category is not supported by the catalog",
                    ", ".join(sorted(self._supported_categories)),
                    inadequate=True,
                )
            updates["category"] = category
        if plan.currency is not None:
            currency_input = self._normalized_text(plan.currency).upper()
            currency = self.CURRENCY_ALIASES.get(currency_input)
            if currency is None:
                self._reject(
                    plan,
                    "currency_unsupported",
                    "currency",
                    "currency is not supported",
                    "DZD or a recognized Algerian dinar alias",
                    inadequate=True,
                )
            updates["currency"] = currency

        if len(plan.specification_constraints) > self.MAX_CONSTRAINTS:
            self._reject(
                plan,
                "constraints_limit_exceeded",
                "specification_constraints",
                "too many specification constraints",
                f"at most {self.MAX_CONSTRAINTS}",
            )
        normalized_constraints = [
            self._normalize_constraint(plan, constraint, index)
            for index, constraint in enumerate(plan.specification_constraints)
        ]
        updates["specification_constraints"] = normalized_constraints

        if len(plan.product_refs) > self.MAX_PRODUCT_REFS:
            self._reject(
                plan,
                "product_refs_limit_exceeded",
                "product_refs",
                "too many product references",
                f"at most {self.MAX_PRODUCT_REFS}",
            )
        for index, reference in enumerate(plan.product_refs):
            if not self._safe_ref.fullmatch(reference):
                self._reject(
                    plan,
                    "product_ref_invalid",
                    f"product_refs.{index}",
                    "product reference contains invalid characters or length",
                    "1-120 printable characters",
                )
        if len(set(plan.product_refs)) != len(plan.product_refs):
            self._reject(
                plan,
                "product_refs_duplicate",
                "product_refs",
                "duplicate product references are ambiguous",
                "unique references",
                inadequate=True,
            )

        if plan.intent is Intent.COMPARISON and len(plan.product_refs) < 2:
            if not plan.needs_clarification:
                self._reject(
                    plan,
                    "comparison_refs_missing",
                    "product_refs",
                    "comparison lacks two explicit product references",
                    "two references or an explicit clarification request",
                    inadequate=True,
                )
        if plan.intent is Intent.UNKNOWN and not plan.needs_clarification:
            self._reject(
                plan,
                "unknown_without_clarification",
                "needs_clarification",
                "unknown intent must request clarification",
                "true",
                inadequate=True,
            )
        if plan.needs_clarification:
            if not plan.missing_info:
                self._reject(
                    plan,
                    "clarification_missing_info",
                    "missing_info",
                    "clarification requires explicit missing information",
                    "a non-empty list",
                    inadequate=True,
                )
            if not plan.clarification_question:
                self._reject(
                    plan,
                    "clarification_question_missing",
                    "clarification_question",
                    "clarification requires a customer-facing question",
                    "a non-empty question",
                    inadequate=True,
                )
        elif plan.missing_info:
            self._reject(
                plan,
                "clarification_state_inconsistent",
                "missing_info",
                "missing information was supplied while clarification is false",
                "[] when needs_clarification is false",
                inadequate=True,
            )
        elif plan.clarification_question is not None:
            self._reject(
                plan,
                "clarification_state_inconsistent",
                "clarification_question",
                "clarification question was supplied while clarification is false",
                "null when needs_clarification is false",
                inadequate=True,
            )

        return plan.model_copy(update=updates)

    def _normalize_constraint(
        self,
        plan: QueryPlan,
        constraint: QuerySpecificationConstraint,
        index: int,
    ) -> QuerySpecificationConstraint:
        path = f"specification_constraints.{index}"
        key_input = self._normalized_text(constraint.key).replace(" ", "_")
        key = self.SPEC_KEY_ALIASES.get(key_input)
        if key is None:
            self._reject(
                plan,
                "spec_key_unsupported",
                f"{path}.key",
                "specification key is not a numeric catalog filter",
                ", ".join(sorted(set(self.SPEC_KEY_ALIASES.values()))),
                inadequate=True,
            )
        if constraint.value < 0:
            self._reject(
                plan,
                "spec_value_negative",
                f"{path}.value",
                "specification value cannot be negative",
                "a non-negative decimal",
            )

        unit = constraint.unit
        if unit is not None:
            unit_input = self._normalized_text(unit)
            normalized_unit = self.SPEC_UNITS[key].get(unit_input)
            if normalized_unit is None:
                self._reject(
                    plan,
                    "spec_unit_unsupported",
                    f"{path}.unit",
                    "unit is incompatible with the specification key",
                    ", ".join(sorted(set(self.SPEC_UNITS[key].values()))),
                    inadequate=True,
                )
            unit = normalized_unit
        return constraint.model_copy(update={"key": key, "unit": unit})

    @staticmethod
    def _normalized_text(value: str) -> str:
        return " ".join(value.strip().casefold().split())

    @staticmethod
    def _reject(
        plan: QueryPlan,
        code: str,
        field_path: str,
        reason: str,
        expected: str | None = None,
        *,
        inadequate: bool = False,
    ) -> None:
        error_type = InadequatePlanError if inadequate else QueryValidationError
        raise error_type(
            code,
            field_path,
            reason,
            expected,
            rejected_plan=plan,
        )
