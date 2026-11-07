"""Complete conversational graph over the deterministic P6 business nodes."""

from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.nodes.analyze import analyze_request_node
from app.agents.nodes.respond import compose_response_node, validate_chat_evidence_node
from app.agents.nodes.sales import (
    SalesFunctionTools,
    compare_products_node,
    lookup_promotions_node,
    rank_recommendations_node,
    route_sales_intent,
    search_products_node,
    unsupported_intent_node,
)
from app.agents.state import ExecutionStatus, ExecutionStep, SalesAgentState
from app.schemas.query_plan import Intent
from app.services.evidence_validator import EvidenceValidator
from app.services.intent_parser import IntentParser
from app.services.response_composer import ResponseComposer


def build_chat_graph(
    parser: IntentParser,
    tools: SalesFunctionTools,
    *,
    checkpointer: BaseCheckpointSaver,
    max_history_messages: int = 30,
) -> CompiledStateGraph:
    composer = ResponseComposer()
    evidence_validator = EvidenceValidator()
    builder = StateGraph(SalesAgentState)
    builder.add_node("analyze_request", lambda state: analyze_request_node(parser, state))
    builder.add_node("search_products", lambda state: search_products_node(tools, state))
    builder.add_node("compare_products", lambda state: compare_products_node(tools, state))
    builder.add_node(
        "rank_recommendations", lambda state: rank_recommendations_node(tools, state)
    )
    builder.add_node("lookup_promotions", lambda state: lookup_promotions_node(tools, state))
    builder.add_node("unsupported_intent", unsupported_intent_node)
    builder.add_node("conversation", _conversation_node)
    builder.add_node(
        "validate_evidence", lambda state: validate_chat_evidence_node(evidence_validator, state)
    )
    builder.add_node(
        "compose_response",
        lambda state: compose_response_node(
            composer, state, max_history_messages=max_history_messages
        ),
    )
    builder.set_entry_point("analyze_request")
    builder.add_conditional_edges("analyze_request", _route_after_analysis)
    for node in (
        "search_products",
        "compare_products",
        "rank_recommendations",
        "lookup_promotions",
    ):
        builder.add_edge(node, "validate_evidence")
    builder.add_edge("validate_evidence", "compose_response")
    builder.add_edge("unsupported_intent", "compose_response")
    builder.add_edge("conversation", "compose_response")
    builder.add_edge("compose_response", END)
    return builder.compile(checkpointer=checkpointer)


def _route_after_analysis(
    state: SalesAgentState,
) -> Literal[
    "search_products",
    "compare_products",
    "rank_recommendations",
    "lookup_promotions",
    "unsupported_intent",
    "conversation",
    "compose_response",
]:
    if state["query_plan"].needs_clarification:
        return "compose_response"
    if state["query_plan"].intent in {
        Intent.GREETING,
        Intent.FAREWELL,
        Intent.GRATITUDE,
        Intent.HELP,
    }:
        return "conversation"
    return route_sales_intent(state)


def _conversation_node(_state: SalesAgentState) -> SalesAgentState:
    return {
        "status": ExecutionStatus.COMPLETED,
        "current_step": ExecutionStep.ROUTE_INTENT,
    }
