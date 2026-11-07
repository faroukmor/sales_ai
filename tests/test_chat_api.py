from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy.orm import Session

from app.agents.checkpoint import chat_checkpoint_serializer
from app.api.dependencies import get_chat_service
from app.db.seed import seed_database
from app.main import app
from app.schemas.chat_response import ChatRequest, ChatStatus
from app.services.chat_service import ChatService
from app.services.intent_parser import IntentParseResult
from app.services.llm_service import LLMUnavailableError
from tests.intent_helpers import make_plan


class StubParser:
    def parse(self, message: str) -> IntentParseResult:
        lowered = message.casefold()
        if "compare" in lowered:
            plan = make_plan(
                message,
                intent="comparison",
                category=None,
                product_refs=[],
                needs_clarification=True,
                missing_info=["product_refs"],
                clarification_question="Which products?",
            )
        elif "recommend" in lowered:
            plan = make_plan(message, intent="recommendation")
        elif "promotion" in lowered or "discount" in lowered:
            plan = make_plan(message, intent="promotion_search", category="laptop")
        elif "explain" in lowered:
            plan = make_plan(message, intent="explanation", category=None)
        else:
            plan = make_plan(message)
        return IntentParseResult(
            plan=plan,
            model_used="stub",
            escalated=False,
            latency_ms=0,
            token_usage={},
            routing_reasons=(),
        )


@pytest.fixture
def chat_service(db_session: Session) -> ChatService:
    seed_database(db_session, date_provider=lambda: date.today())
    return ChatService(
        db_session,
        StubParser(),  # type: ignore[arg-type]
        InMemorySaver(serde=chat_checkpoint_serializer()),
    )


def post(service: ChatService, payload: dict[str, Any]):
    app.dependency_overrides[get_chat_service] = lambda: service
    try:
        return TestClient(app).post("/api/chat", json=payload)
    finally:
        app.dependency_overrides.clear()


def test_chat_product_search_and_serialization(chat_service: ChatService) -> None:
    response = post(chat_service, {"message": "Find laptops"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["intent"] == "product_search"
    assert body["language"] == "en"
    assert body["session_id"]
    assert body["products"]
    assert body["comparison"] is None
    assert body["recommendations"] == []
    assert body["promotions"] == []
    assert body["sources"]


def test_chat_request_validation(chat_service: ChatService) -> None:
    assert post(chat_service, {"message": ""}).status_code == 422
    assert post(chat_service, {"message": "x" * 2001}).status_code == 422
    assert post(chat_service, {"message": "hello", "session_id": "guessable"}).status_code == 422


def test_recommendation_and_promotion_responses(chat_service: ChatService) -> None:
    recommendation = post(chat_service, {"message": "Recommend a laptop"}).json()
    promotion = post(chat_service, {"message": "Show laptop promotions"}).json()
    assert recommendation["recommendations"][0]["rank"] == 1
    assert recommendation["recommendations"][0]["score"]
    assert promotion["promotions"][0]["title"] == "TEST-PROMO-01"


def test_session_continuity_and_isolation(chat_service: ChatService) -> None:
    search = post(chat_service, {"message": "Find laptops"}).json()
    continued = post(
        chat_service,
        {"message": "Compare the first two", "session_id": search["session_id"]},
    ).json()
    isolated = post(chat_service, {"message": "Compare the first two"}).json()

    assert continued["status"] == "ok"
    assert len(continued["comparison"]["product_ids"]) >= 2
    assert isolated["status"] == "needs_clarification"


def test_unsupported_rag_request_is_controlled(chat_service: ChatService) -> None:
    first = post(chat_service, {"message": "Find laptops"}).json()
    body = post(
        chat_service,
        {"message": "Explain OLED burn-in", "session_id": first["session_id"]},
    ).json()
    assert body["status"] == "insufficient_evidence"
    assert body["sources"] == []
    assert body["products"] == []


def test_chat_response_models_every_supported_status() -> None:
    request = ChatRequest(message="hello")
    assert request.session_id is None
    assert {item.value for item in ChatStatus} == {
        "ok",
        "no_results",
        "needs_clarification",
        "product_not_found",
        "insufficient_evidence",
        "not_supported",
        "error",
    }


def test_provider_failure_is_sanitized() -> None:
    class BrokenService:
        def chat(self, _request):
            raise LLMUnavailableError("secret provider detail")

    response = post(BrokenService(), {"message": "Find laptops"})  # type: ignore[arg-type]
    assert response.status_code == 502
    assert "secret" not in response.text


def test_checkpoint_message_history_is_bounded(db_session: Session) -> None:
    seed_database(db_session, date_provider=lambda: date.today())
    service = ChatService(
        db_session,
        StubParser(),  # type: ignore[arg-type]
        InMemorySaver(serde=chat_checkpoint_serializer()),
        max_history_messages=4,
    )
    session_id = None
    for _ in range(4):
        response = service.chat(ChatRequest(message="Find laptops", session_id=session_id))
        session_id = response.session_id
    snapshot = service._graph.get_state(  # noqa: SLF001 - checkpoint contract assertion
        {"configurable": {"thread_id": session_id}}
    )
    assert len(snapshot.values["messages"]) <= 4
