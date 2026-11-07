from datetime import date

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy.orm import Session

from app.agents.checkpoint import chat_checkpoint_serializer
from app.db.seed import seed_database
from app.schemas.chat_response import ChatRequest
from app.schemas.query_plan import Intent, Language
from app.services.chat_service import ChatService
from app.services.conversation_classifier import classify_conversation
from tests.test_chat_api import StubParser


@pytest.mark.parametrize(
    ("message", "intent", "language"),
    [
        ("hi", Intent.GREETING, Language.EN),
        ("bonjour", Intent.GREETING, Language.FR),
        ("سلام", Intent.GREETING, Language.AR),
        ("salam", Intent.GREETING, Language.DZ),
        ("thanks", Intent.GRATITUDE, Language.EN),
        ("merci", Intent.GRATITUDE, Language.FR),
        ("chokrane", Intent.GRATITUDE, Language.DZ),
        ("bye", Intent.FAREWELL, Language.EN),
        ("بسلامة", Intent.FAREWELL, Language.DZ),
        ("واش تقدر تدير؟", Intent.HELP, Language.DZ),
        ("what can you do?", Intent.HELP, Language.EN),
    ],
)
def test_bounded_conversation_classifier(message, intent, language) -> None:
    plan = classify_conversation(message)
    assert plan is not None
    assert plan.intent is intent
    assert plan.language is language
    assert plan.category is None


@pytest.fixture
def service(db_session: Session) -> ChatService:
    seed_database(db_session, date_provider=lambda: date.today())
    return ChatService(
        db_session,
        StubParser(),  # type: ignore[arg-type]
        InMemorySaver(serde=chat_checkpoint_serializer()),
    )


@pytest.mark.parametrize(
    ("message", "intent", "language", "expected"),
    [
        ("hi", "greeting", "en", "Hello"),
        ("bonjour", "greeting", "fr", "Bonjour"),
        ("سلام", "greeting", "ar", "مرحباً"),
        ("واش تقدر تدير؟", "help", "dz", "نقدر"),
        ("thanks", "gratitude", "en", "welcome"),
    ],
)
def test_conversational_chat_responses(service, message, intent, language, expected) -> None:
    response = service.chat(ChatRequest(message=message))
    assert response.status.value == "ok"
    assert response.intent.value == intent
    assert response.language.value == language
    assert expected.casefold() in response.answer.casefold()
    assert response.products == []


def test_conversational_intents_do_not_call_provider(db_session: Session) -> None:
    seed_database(db_session, date_provider=lambda: date.today())

    class ProviderMustNotRun:
        def parse(self, _message):
            raise AssertionError("Groq parser should not run for bounded conversation intents")

    service = ChatService(
        db_session,
        ProviderMustNotRun(),  # type: ignore[arg-type]
        InMemorySaver(serde=chat_checkpoint_serializer()),
    )
    assert service.chat(ChatRequest(message="hello")).intent is Intent.GREETING
    assert service.chat(ChatRequest(message="merci")).intent is Intent.GRATITUDE


def test_greeting_preserves_products_for_later_comparison(service: ChatService) -> None:
    search = service.chat(ChatRequest(message="Find laptops"))
    greeting = service.chat(ChatRequest(message="hi", session_id=search.session_id))
    comparison = service.chat(
        ChatRequest(message="Compare the first two", session_id=search.session_id)
    )

    assert greeting.intent is Intent.GREETING
    assert comparison.intent is Intent.COMPARISON
    assert comparison.comparison is not None
    assert len(comparison.comparison.product_ids) >= 2


@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("Find laptops", Intent.PRODUCT_SEARCH),
        ("Recommend a laptop", Intent.RECOMMENDATION),
        ("Show laptop promotions", Intent.PROMOTION_SEARCH),
    ],
)
def test_business_route_regression(service: ChatService, message: str, intent: Intent) -> None:
    response = service.chat(ChatRequest(message=message))
    assert response.intent is intent
    assert response.status.value in {"ok", "no_results"}
