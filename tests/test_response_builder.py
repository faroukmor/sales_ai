# tests/test_response_builder.py
from models.chat_response import Status
from models.chunk import Chunk, ScoredChunk
from models.comparison import ComparisonResult, ComparisonRow
from models.evidence import EvidenceBundle
from models.product import Product
from models.query_plan import Intent, QueryPlan
from services.response_builder import ResponseBuilder

b = ResponseBuilder()


def plan(intent, language="en", **kw):
    return QueryPlan(message="m", intent=intent, language=language, **kw)


def prod(pid=1):
    return Product(id=pid, name=f"P{pid}", category="laptop", currency="DZD", price=1.0)


def test_search_with_products_is_ok():
    r = b.build(plan(Intent.PRODUCT_SEARCH), EvidenceBundle(products=(prod(1), prod(2))))
    assert r.status is Status.OK and len(r.products) == 2 and "2" in r.answer


def test_search_without_products_is_no_results():
    r = b.build(plan(Intent.PRODUCT_SEARCH), EvidenceBundle())
    assert r.status is Status.NO_RESULTS and r.products == ()


def test_answer_language_follows_plan():
    r = b.build(plan(Intent.PRODUCT_SEARCH, "ar"), EvidenceBundle())
    assert "لا توجد منتجات" in r.answer
    r = b.build(plan(Intent.PRODUCT_SEARCH, "fr"), EvidenceBundle())
    assert "Aucun produit" in r.answer


def test_unknown_language_falls_back_to_english():
    r = b.build(plan(Intent.PRODUCT_SEARCH, "unknown"), EvidenceBundle())
    assert r.answer.startswith("No products match")


def test_comparison_missing_ambiguous_and_incomplete():
    r = b.build(plan(Intent.COMPARISON), EvidenceBundle(missing_refs=("Nope",)))
    assert r.status is Status.PRODUCT_NOT_FOUND and "Nope" in r.answer
    r = b.build(plan(Intent.COMPARISON), EvidenceBundle(ambiguous_refs=("Laptop",)))
    assert r.status is Status.NEEDS_CLARIFICATION
    r = b.build(plan(Intent.COMPARISON), EvidenceBundle())
    assert r.status is Status.NEEDS_CLARIFICATION


def test_comparison_text_marks_missing_values():
    comparison = ComparisonResult(
        product_names=("A", "B"),
        rows=(ComparisonRow("price", ("100 DZD", None), differs=False, has_missing=True),),
    )
    r = b.build(plan(Intent.COMPARISON), EvidenceBundle(products=(prod(1), prod(2)), comparison=comparison))
    assert r.status is Status.OK and r.comparison is comparison
    assert "price: 100 DZD | n/a" in r.answer


def test_explanation_with_text_has_deduplicated_sources():
    c1 = ScoredChunk(Chunk(1, "a.txt", "t", title="Doc A"), 0.9)
    c1b = ScoredChunk(Chunk(1, "a.txt", "t2", title="Doc A"), 0.8)
    c2 = ScoredChunk(Chunk(2, "b.txt", "t"), 0.7)
    r = b.build(plan(Intent.EXPLANATION), EvidenceBundle(chunks=(c1, c1b, c2)), "Answer text")
    assert r.status is Status.OK and r.answer == "Answer text"
    assert [(s.label, s.chunk_id) for s in r.sources] == [("Doc A", 1), ("b.txt", 2)]


def test_explanation_without_text_or_chunks_is_insufficient():
    chunk = ScoredChunk(Chunk(1, "a.txt", "t"), 0.9)
    assert b.build(plan(Intent.EXPLANATION), EvidenceBundle(chunks=(chunk,)), None).status is Status.INSUFFICIENT_EVIDENCE
    assert b.build(plan(Intent.EXPLANATION), EvidenceBundle(), "text").status is Status.INSUFFICIENT_EVIDENCE


def test_clarification_messages_by_missing_info():
    assert "kind of product" in b.needs_clarification(plan(Intent.PRODUCT_SEARCH, missing_info=("category",))).answer
    assert "at least two" in b.needs_clarification(plan(Intent.COMPARISON, missing_info=("products_to_compare",))).answer
    assert "maximum budget" in b.needs_clarification(plan(Intent.PRODUCT_SEARCH, missing_info=("price_bound",))).answer
    unknown = b.needs_clarification(plan(Intent.UNKNOWN))
    assert unknown.status is Status.NEEDS_CLARIFICATION and "not sure" in unknown.answer


def test_error_and_unsupported():
    assert b.error(plan(Intent.EXPLANATION)).status is Status.ERROR
    assert b.build(plan(Intent.PROMOTION_SEARCH), EvidenceBundle()).status is Status.NOT_SUPPORTED


def test_response_carries_intent_and_language():
    r = b.error(plan(Intent.COMPARISON, "fr"))
    assert r.intent is Intent.COMPARISON and r.language == "fr"
