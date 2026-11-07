from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.db.seed import seed_database
from app.repositories.product_repository import ProductRepository
from app.schemas.query_plan import QuerySpecificationConstraint
from app.schemas.sales_functions import ToolStatus
from app.services.recommendation import RecommendationService
from tests.intent_helpers import make_plan


@pytest.fixture
def service(db_session: Session) -> RecommendationService:
    seed_database(db_session, date_provider=lambda: date(2026, 6, 15))
    return RecommendationService(ProductRepository(db_session))


def programming_plan(max_price: Decimal = Decimal("120000")):
    return make_plan(
        "laptop for programming with 16 GB RAM",
        intent="recommendation",
        category="laptop",
        max_price=max_price,
        currency="DZD",
        in_stock_only=True,
        specification_constraints=[
            QuerySpecificationConstraint(key="ram_gb", operator="gte", value=16, unit="GB")
        ],
    )


def test_recommendations_are_deterministic_and_explainable(service) -> None:
    first = service.recommend(programming_plan())
    second = service.recommend(programming_plan())

    assert first == second
    assert first.status is ToolStatus.SUCCESS
    assert [item.rank for item in first.recommendations] == [1]
    assert first.recommendations[0].reasons
    assert first.recommendations[0].score <= 1


def test_products_outside_budget_are_excluded(service) -> None:
    result = service.recommend(programming_plan(Decimal("90000")))
    assert result.status is ToolStatus.NO_RESULTS
    assert result.recommendations == []


def test_missing_specs_are_reported_safely(service) -> None:
    plan = make_plan("recommend a TV", intent="recommendation", category="tv")
    result = service.recommend(plan)
    assert result.status is ToolStatus.SUCCESS
    assert "ram_gb" in result.recommendations[0].missing_specifications


def test_scores_are_in_descending_order(service) -> None:
    plan = make_plan("recommend a laptop", intent="recommendation", category="laptop")
    result = service.recommend(plan)
    scores = [item.score for item in result.recommendations]
    assert scores == sorted(scores, reverse=True)


def test_no_eligible_candidates(service) -> None:
    plan = make_plan("recommend Acme", intent="recommendation", brand="Acme")
    assert service.recommend(plan).status is ToolStatus.NO_RESULTS


def test_ambiguous_requirements_request_clarification(service) -> None:
    plan = make_plan(
        "recommend something",
        intent="recommendation",
        needs_clarification=True,
        missing_info=["category"],
        clarification_question="Which category?",
    )
    result = service.recommend(plan)
    assert result.status is ToolStatus.INSUFFICIENT_INFORMATION
    assert result.message == "Which category?"
