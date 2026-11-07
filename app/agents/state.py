"""Shared state contract for the future Sales AI LangGraph.

Nodes must return partial dictionaries containing only the keys they own.  An absent
optional key means that its stage has not run; an empty collection means that the stage
ran successfully and produced no results.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, TypedDict
from uuid import uuid4

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductRead
from app.schemas.promotion import PromotionRead
from app.schemas.query_plan import Intent, Language, QueryPlan
from app.schemas.sales_functions import RecommendationItem


class ExecutionStatus(StrEnum):
    """Controlled lifecycle values shared by graph nodes and API adapters."""

    READY = "ready"
    RUNNING = "running"
    NEEDS_CLARIFICATION = "needs_clarification"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionStep(StrEnum):
    """Current or most recently completed graph stage."""

    INITIALIZED = "initialized"
    ANALYZE_REQUEST = "analyze_request"
    ROUTE_INTENT = "route_intent"
    SEARCH_PRODUCTS = "search_products"
    COMPARE_PRODUCTS = "compare_products"
    RETRIEVE_KNOWLEDGE = "retrieve_knowledge"
    RANK_RECOMMENDATIONS = "rank_recommendations"
    VALIDATE_EVIDENCE = "validate_evidence"
    COMPOSE_RESPONSE = "compose_response"
    CLARIFY = "clarify"


class StateError(BaseModel):
    """Safe, structured error recorded by a node without exception objects or secrets."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=500)
    step: ExecutionStep
    retryable: bool = False
    field_path: str | None = Field(default=None, max_length=200)


class EvidenceItem(BaseModel):
    """A claim-supporting excerpt and its stable source reference."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    source_id: str = Field(min_length=1, max_length=255)
    source_type: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)
    url: str | None = None
    product_id: int | None = None


class ComparisonValue(BaseModel):
    """One product value in a comparison row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    product_id: int
    value: str | int | float | bool | None


class ComparisonRow(BaseModel):
    """One normalized attribute compared across products."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    attribute: str = Field(min_length=1, max_length=100)
    values: list[ComparisonValue]


class ProductComparison(BaseModel):
    """Structured comparison output; prose belongs in ``answer``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    product_ids: list[int] = Field(min_length=2)
    rows: list[ComparisonRow]


class SalesAgentState(TypedDict, total=False):
    """LangGraph-compatible state shared through partial node updates.

    The state stores validated/read schemas rather than ORM entities.  It must never hold
    database sessions, model clients, credentials, or duplicated transcript strings.
    """

    # Conversation (initializer; messages are append/replace merged by LangGraph).
    messages: Annotated[list[AnyMessage], add_messages]
    session_id: str
    user_id: str

    # Understanding (analyze_request).
    query_plan: QueryPlan
    intent: Intent
    language: Language
    missing_info: list[str]

    # Business results (search/compare/retrieve/rank nodes).
    products: list[ProductRead]
    comparison: ProductComparison | None
    promotions: list[PromotionRead]
    evidence: list[EvidenceItem]
    recommendations: list[RecommendationItem]

    # Response and execution metadata.
    answer: str
    status: ExecutionStatus
    errors: list[StateError]
    current_step: ExecutionStep
    last_product_ids: list[int]


def create_initial_state(
    user_message: str,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
) -> SalesAgentState:
    """Create isolated state for one conversation without invoking the graph or an LLM."""

    if not isinstance(user_message, str):
        raise TypeError("user_message must be a string")
    if not user_message.strip():
        raise ValueError("user_message must not be empty")
    if session_id is not None and not session_id.strip():
        raise ValueError("session_id must not be empty")
    if user_id is not None and not user_id.strip():
        raise ValueError("user_id must not be empty")

    state: SalesAgentState = {
        "messages": [HumanMessage(content=user_message)],
        "session_id": session_id or str(uuid4()),
        "status": ExecutionStatus.READY,
        "errors": [],
        "current_step": ExecutionStep.INITIALIZED,
        "missing_info": [],
        "last_product_ids": [],
    }
    if user_id is not None:
        state["user_id"] = user_id
    return state
