# tests/test_knowledge_retriever.py
import pytest

from core.exceptions import EmbeddingError
from rag.knowledge_ingestor import KnowledgeIngestor, split_paragraphs
from rag.knowledge_retriever import KnowledgeRetriever


class FakeEmbedder:
    """متجهات ثابتة لنصوص معروفة: نتحكم بالتشابه بدقة دون Ollama."""
    model = "fake-embed"

    def __init__(self, table):
        self.table = table
        self.calls = 0

    def embed(self, text):
        self.calls += 1
        if text in self.table:                      # تطابق تام أولًا
            return self.table[text]
        for key in sorted(self.table, key=len, reverse=True):
            if key in text:
                return self.table[key]
        raise EmbeddingError(f"no fake vector for: {text}")


TABLE = {
    "OLED": [1.0, 0.0, 0.0],
    "RAM": [0.0, 1.0, 0.0],
    "QUERY-OLED": [0.9, 0.1, 0.0],      # قريب من OLED
    "QUERY-NONE": [0.0, 0.0, 1.0],      # لا يقترب من أي مقطع
}


@pytest.fixture
def kb(conn):
    embedder = FakeEmbedder(TABLE)
    ingestor = KnowledgeIngestor(conn, embedder)
    ingestor.add_document("oled.txt", "OLED panels emit light per pixel.", title="OLED guide")
    ingestor.add_document("ram.txt", "RAM is working memory.")
    return conn, embedder


def test_returns_relevant_chunk_first_with_metadata(kb):
    conn, embedder = kb
    results = KnowledgeRetriever(conn, embedder, min_similarity=0.5).retrieve("QUERY-OLED")
    assert results[0].chunk.title == "OLED guide"
    assert results[0].chunk.source == "oled.txt"
    assert results[0].score > 0.9
    assert all(r.score >= 0.5 for r in results)


def test_nothing_relevant_returns_empty_list(kb):
    conn, embedder = kb
    assert KnowledgeRetriever(conn, embedder, min_similarity=0.5).retrieve("QUERY-NONE") == []


def test_top_k_limits_results(kb):
    conn, embedder = kb
    results = KnowledgeRetriever(conn, embedder, top_k=1, min_similarity=-1.0).retrieve("QUERY-OLED")
    assert len(results) == 1


def test_empty_knowledge_base_does_not_call_the_embedder(conn):
    embedder = FakeEmbedder(TABLE)
    assert KnowledgeRetriever(conn, embedder).retrieve("QUERY-OLED") == []
    assert embedder.calls == 0


def test_chunks_from_another_embedding_model_are_ignored(kb):
    conn, embedder = kb
    other = FakeEmbedder(TABLE)
    other.model = "different-model"
    assert KnowledgeRetriever(conn, other, min_similarity=0.0).retrieve("QUERY-OLED") == []


def test_chunks_with_wrong_dimension_are_skipped(kb):
    conn, embedder = kb
    wrong = FakeEmbedder({**TABLE, "QUERY-OLED": [1.0, 0.0]})   # بُعد 2 بدل 3
    wrong.model = embedder.model
    assert KnowledgeRetriever(conn, wrong, min_similarity=0.0).retrieve("QUERY-OLED") == []


def test_zero_vector_query_returns_empty(kb):
    conn, embedder = kb
    zero = FakeEmbedder({"QUERY-ZERO": [0.0, 0.0, 0.0]})
    zero.model = embedder.model
    assert KnowledgeRetriever(conn, zero, min_similarity=-1.0).retrieve("QUERY-ZERO") == []


def test_embedding_failure_propagates_as_embedding_error(kb):
    conn, embedder = kb
    with pytest.raises(EmbeddingError):
        KnowledgeRetriever(conn, embedder).retrieve("unknown query")


# ---------- الإدخال (ingestion) ----------

def test_reingesting_a_source_replaces_its_chunks(kb):
    conn, embedder = kb
    KnowledgeIngestor(conn, embedder).add_document("oled.txt", "OLED new text.")
    texts = [r[0] for r in conn.execute("SELECT text FROM knowledge_chunks WHERE source='oled.txt'")]
    assert texts == ["OLED new text."]


def test_failed_embedding_leaves_existing_chunks_untouched(kb):
    conn, embedder = kb
    with pytest.raises(EmbeddingError):
        KnowledgeIngestor(conn, embedder).add_document("oled.txt", "OLED ok.\n\nunembeddable paragraph")
    texts = [r[0] for r in conn.execute("SELECT text FROM knowledge_chunks WHERE source='oled.txt'")]
    assert texts == ["OLED panels emit light per pixel."]


def test_split_paragraphs():
    assert split_paragraphs("one\ntwo\n\nthree") == ["one two", "three"]
    long = ("word " * 50).strip()
    parts = split_paragraphs(long, max_chars=60)
    assert all(len(p) <= 60 for p in parts) and " ".join(parts) == long
    assert split_paragraphs("   \n\n  ") == []


def test_add_directory_reads_txt_and_md_only(conn, tmp_path):
    (tmp_path / "a.txt").write_text("OLED text", encoding="utf-8")
    (tmp_path / "b.md").write_text("RAM text", encoding="utf-8")
    (tmp_path / "c.pdf").write_text("ignored", encoding="utf-8")
    report = KnowledgeIngestor(conn, FakeEmbedder(TABLE)).add_directory(tmp_path)
    assert report == {"a.txt": 1, "b.md": 1}
