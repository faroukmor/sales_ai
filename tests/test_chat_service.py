# tests/test_chat_service.py
import pytest

from core.exceptions import EmbeddingError, GenerationError
from handlers.comparison_handler import ComparisonHandler
from handlers.explanation_handler import ExplanationHandler
from handlers.search_handler import SearchHandler
from models.chat_response import Status
from models.chunk import Chunk, ScoredChunk
from models.query_plan import Intent
from services.answer_validator import AnswerValidator
from services.chat_service import ChatService
from services.product_comparator import ProductComparator
from services.query_analyzer import QueryAnalyzer
from services.response_builder import ResponseBuilder

EVIDENCE = [ScoredChunk(Chunk(1, "oled.txt", "OLED pixels emit their own light. Contrast is high.", title="OLED guide"), 0.9)]


class FakeRetriever:
    def __init__(self, results=None, error=None):
        self.results, self.error = results or [], error

    def retrieve(self, query):
        if self.error:
            raise self.error
        return self.results


class FakeGenerator:
    def __init__(self, text="OLED pixels emit light.", error=None):
        self.text, self.error, self.calls = text, error, 0

    def generate(self, question, chunks, language):
        self.calls += 1
        if self.error:
            raise self.error
        return self.text


@pytest.fixture
def make_service(repo):
    def _make(retriever=None, generator=None):
        handlers = {
            Intent.PRODUCT_SEARCH: SearchHandler(repo),
            Intent.COMPARISON: ComparisonHandler(repo, ProductComparator()),
            Intent.EXPLANATION: ExplanationHandler(retriever or FakeRetriever(EVIDENCE)),
        }
        gen = generator or FakeGenerator()
        service = ChatService(QueryAnalyzer(), handlers, ResponseBuilder(), gen, AnswerValidator())
        return service, gen
    return _make


# ---------- بحث: كامل ودون أي LLM ----------

def test_product_search_end_to_end_without_llm(make_service):
    service, gen = make_service()
    r = service.handle_message("Find a laptop under 100,000 DZD with at least 16 GB RAM")
    assert r.status is Status.OK and r.intent is Intent.PRODUCT_SEARCH
    assert [p.name for p in r.products] == ["Test Laptop A"]
    assert gen.calls == 0


def test_search_with_no_match(make_service):
    r = make_service()[0].handle_message("Find a laptop under 1000 DZD")
    assert r.status is Status.NO_RESULTS and r.products == ()


# ---------- التوضيح ----------

def test_missing_category_asks_for_clarification_and_skips_repository(make_service):
    r = make_service()[0].handle_message("I want something under 50000 DZD")
    assert r.status is Status.NEEDS_CLARIFICATION and r.products == ()


def test_unknown_message_asks_for_clarification(make_service):
    assert make_service()[0].handle_message("hello").status is Status.NEEDS_CLARIFICATION


def test_clarification_is_in_the_users_language(make_service):
    r = make_service()[0].handle_message("أريد لابتوب")
    assert r.language == "ar" and "ثم" not in r.answer and r.status is Status.NEEDS_CLARIFICATION


# ---------- مقارنة ----------

def test_comparison_end_to_end(make_service):
    r = make_service()[0].handle_message("Compare Test Laptop A and Test Laptop B")
    assert r.status is Status.OK and r.comparison is not None
    assert [p.name for p in r.products] == ["Test Laptop A", "Test Laptop B"]


def test_comparison_with_unknown_product(make_service):
    r = make_service()[0].handle_message("Compare Test Laptop A and Ghost")
    assert r.status is Status.PRODUCT_NOT_FOUND and "Ghost" in r.answer


def test_comparison_with_incomplete_specs_marks_missing(make_service):
    r = make_service()[0].handle_message("Compare Test Laptop A and Test Laptop E")
    ram_row = next(row for row in r.comparison.rows if row.key == "ram_gb")
    assert ram_row.values[1] is None and ram_row.has_missing


# ---------- شرح (RAG + LLM) ----------

def test_explanation_returns_generated_text_with_sources(make_service):
    service, gen = make_service()
    r = service.handle_message("What is the difference between OLED and QLED?")
    assert r.status is Status.OK and r.answer == "OLED pixels emit light."
    assert [s.label for s in r.sources] == ["OLED guide"] and gen.calls == 1


def test_explanation_without_evidence_never_calls_the_llm(make_service):
    service, gen = make_service(retriever=FakeRetriever([]))
    r = service.handle_message("What is OLED?")
    assert r.status is Status.INSUFFICIENT_EVIDENCE and gen.calls == 0


def test_model_saying_no_answer_gives_insufficient_evidence(make_service):
    service, _ = make_service(generator=FakeGenerator(text=None))
    assert service.handle_message("What is OLED?").status is Status.INSUFFICIENT_EVIDENCE


def test_answer_with_unsupported_number_is_discarded(make_service):
    service, _ = make_service(generator=FakeGenerator(text="OLED lasts 99999 hours."))
    r = service.handle_message("What is OLED?")
    assert r.status is Status.INSUFFICIENT_EVIDENCE and "99999" not in r.answer


# ---------- أخطاء Ollama ----------

def test_generation_error_becomes_error_response(make_service):
    service, _ = make_service(generator=FakeGenerator(error=GenerationError("down")))
    r = service.handle_message("What is OLED?")
    assert r.status is Status.ERROR and r.sources == ()


def test_embedding_error_becomes_error_response(make_service):
    service, _ = make_service(retriever=FakeRetriever(error=EmbeddingError("down")))
    assert service.handle_message("What is OLED?").status is Status.ERROR


def test_search_still_works_when_ollama_is_down(make_service):
    service, _ = make_service(retriever=FakeRetriever(error=EmbeddingError("down")),
                              generator=FakeGenerator(error=GenerationError("down")))
    assert service.handle_message("Find a laptop under 100000 DZD").status is Status.OK


# ---------- نيات غير مدعومة بعد ----------

def test_promotion_intent_is_not_supported_yet(make_service):
    r = make_service()[0].handle_message("Are there any promotions on laptops?")
    assert r.status is Status.NOT_SUPPORTED


def test_response_is_always_consistent(make_service):
    service, _ = make_service()
    for message in ["Find a laptop", "hello", "Compare Test Laptop A and Ghost", "What is OLED?",
                    "Find a laptop under 100000 DZD"]:
        r = service.handle_message(message)
        assert isinstance(r.answer, str) and r.answer
        assert isinstance(r.status, Status) and isinstance(r.intent, Intent)
