from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.agents.nodes.sales import SalesFunctionTools
from app.agents.sales_graph import build_sales_functions_graph
from app.agents.state import ExecutionStatus, create_initial_state
from app.db.seed import seed_database
from app.repositories.product_repository import ProductRepository
from app.repositories.promotion_repository import PromotionRepository
from app.schemas.query_plan import QuerySpecificationConstraint
from app.services.recommendation import RecommendationService
from app.tools.product_comparison import ProductComparisonTool
from app.tools.product_search import ProductSearchTool
from app.tools.promotions import PromotionsTool
from tests.intent_helpers import make_plan

TODAY = date(2026, 6, 15)


@pytest.fixture
def sales_graph(db_session: Session):
    seed_database(db_session, date_provider=lambda: TODAY)
    products = ProductRepository(db_session)
    promotions = PromotionRepository(db_session, date_provider=lambda: TODAY)
    tools = SalesFunctionTools(
        search=ProductSearchTool(products),
        comparison=ProductComparisonTool(products, promotions),
        recommendations=RecommendationService(products),
        promotions=PromotionsTool(promotions, products),
    )
    return build_sales_functions_graph(tools), products


@pytest.mark.parametrize(
    ("message", "language"),
    [
        ("Find a laptop under 100000 DA with 16GB RAM", "en"),
        ("Je cherche un PC avec 16 Go de RAM", "fr"),
        ("نحب PC محمول فيه 16 جيغا رام", "ar"),
        ("عطيني PC مليح فيه 16GB RAM", "dz"),
    ],
)
def test_multilingual_normalized_search_is_grounded(sales_graph, message, language) -> None:
    graph, _ = sales_graph
    plan = make_plan(
        message,
        language=language,
        category="laptop",
        max_price=Decimal("100000"),
        specification_constraints=[
            QuerySpecificationConstraint(key="ram_gb", operator="gte", value=16, unit="GB")
        ],
    )
    result = graph.invoke({**create_initial_state(message), "query_plan": plan})

    assert result["status"] == ExecutionStatus.COMPLETED
    assert [product.name for product in result["products"]] == ["TEST-LAPTOP-01"]
    assert all(item.source_id.startswith("product:") for item in result["evidence"])


def test_graph_routes_comparison_with_session_context(sales_graph) -> None:
    graph, products = sales_graph
    ids = [
        products.find_by_name("TEST-LAPTOP-01")[0].id,
        products.find_by_name("TEST-LAPTOP-02")[0].id,
    ]
    plan = make_plan("compare the first two", intent="comparison", product_refs=[])
    result = graph.invoke(
        {**create_initial_state(plan.original_message), "query_plan": plan, "last_product_ids": ids}
    )
    assert result["comparison"].product_ids == ids


def test_graph_routes_recommendations(sales_graph) -> None:
    graph, _ = sales_graph
    plan = make_plan("recommend a laptop", intent="recommendation", category="laptop")
    result = graph.invoke({**create_initial_state(plan.original_message), "query_plan": plan})
    assert result["recommendations"]
    assert result["recommendations"][0].rank == 1


def test_graph_routes_active_promotions(sales_graph) -> None:
    graph, _ = sales_graph
    plan = make_plan("current laptop promotions", intent="promotion_search", category="laptop")
    result = graph.invoke({**create_initial_state(plan.original_message), "query_plan": plan})
    assert [promotion.title for promotion in result["promotions"]] == ["TEST-PROMO-01"]


def test_unsupported_intent_has_controlled_failure(sales_graph) -> None:
    graph, _ = sales_graph
    plan = make_plan("hello", intent="greeting", category=None)
    result = graph.invoke({**create_initial_state(plan.original_message), "query_plan": plan})
    assert result["status"] == ExecutionStatus.FAILED
    assert result["errors"][-1].code == "unsupported_intent"
