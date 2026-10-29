# tests/test_handlers.py
from handlers.comparison_handler import ComparisonHandler
from handlers.explanation_handler import ExplanationHandler
from handlers.search_handler import SearchHandler
from models.chunk import Chunk, ScoredChunk
from models.query_plan import Comparison, Intent, ProductFilters, QueryPlan, SpecConstraint
from services.product_comparator import ProductComparator


def test_search_handler_uses_plan_filters(repo):
    plan = QueryPlan("m", Intent.PRODUCT_SEARCH, filters=ProductFilters(
        category="laptop", max_price=100000,
        spec_constraints=(SpecConstraint("ram_gb", Comparison.GTE, 16),)))
    bundle = SearchHandler(repo).handle(plan)
    assert [p.name for p in bundle.products] == ["Test Laptop A"]
    assert bundle.chunks == () and bundle.comparison is None


def comparison_plan(*refs):
    return QueryPlan("m", Intent.COMPARISON, product_refs=refs)


def test_comparison_handler_resolves_and_compares(repo):
    bundle = ComparisonHandler(repo, ProductComparator()).handle(
        comparison_plan("Test Laptop A", "Test Laptop B"))
    assert [p.name for p in bundle.products] == ["Test Laptop A", "Test Laptop B"]
    assert bundle.comparison is not None and bundle.missing_refs == ()


def test_comparison_handler_reports_missing_products(repo):
    bundle = ComparisonHandler(repo, ProductComparator()).handle(
        comparison_plan("Test Laptop A", "Ghost"))
    assert bundle.missing_refs == ("Ghost",) and bundle.comparison is None


def test_comparison_handler_reports_ambiguous_names(repo):
    bundle = ComparisonHandler(repo, ProductComparator()).handle(
        comparison_plan("Test Laptop", "Test TV A"))
    assert bundle.ambiguous_refs == ("Test Laptop",) and bundle.comparison is None


def test_comparison_handler_ignores_duplicates(repo):
    bundle = ComparisonHandler(repo, ProductComparator()).handle(
        comparison_plan("Test Laptop A", "test laptop a"))
    assert len(bundle.products) == 1 and bundle.comparison is None


class FakeRetriever:
    def __init__(self, results):
        self.results, self.queries = results, []

    def retrieve(self, query):
        self.queries.append(query)
        return self.results


def test_explanation_handler_passes_message_and_wraps_chunks():
    chunk = ScoredChunk(Chunk(1, "a.txt", "text"), 0.9)
    retriever = FakeRetriever([chunk])
    bundle = ExplanationHandler(retriever).handle(QueryPlan("what is OLED", Intent.EXPLANATION))
    assert retriever.queries == ["what is OLED"] and bundle.chunks == (chunk,)
