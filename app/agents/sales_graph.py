"""Minimal P6 LangGraph wiring over prevalidated QueryPlan state."""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.nodes.sales import (
    SalesFunctionTools,
    compare_products_node,
    lookup_promotions_node,
    rank_recommendations_node,
    route_sales_intent,
    search_products_node,
    unsupported_intent_node,
    validate_evidence_node,
)
from app.agents.state import ExecutionStep, SalesAgentState


def build_sales_functions_graph(tools: SalesFunctionTools) -> CompiledStateGraph:
    """Build the deterministic business portion of the future full conversation graph."""

    builder = StateGraph(SalesAgentState)
    builder.add_node("route_intent", lambda _state: {"current_step": ExecutionStep.ROUTE_INTENT})
    builder.add_node("search_products", lambda state: search_products_node(tools, state))
    builder.add_node("compare_products", lambda state: compare_products_node(tools, state))
    builder.add_node(
        "rank_recommendations", lambda state: rank_recommendations_node(tools, state)
    )
    builder.add_node("lookup_promotions", lambda state: lookup_promotions_node(tools, state))
    builder.add_node("unsupported_intent", unsupported_intent_node)
    builder.add_node("validate_evidence", validate_evidence_node)
    builder.set_entry_point("route_intent")
    builder.add_conditional_edges("route_intent", route_sales_intent)
    for node in (
        "search_products",
        "compare_products",
        "rank_recommendations",
        "lookup_promotions",
    ):
        builder.add_edge(node, "validate_evidence")
    builder.add_edge("validate_evidence", END)
    builder.add_edge("unsupported_intent", END)
    return builder.compile()
