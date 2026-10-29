# rag/knowledge_retriever.py
import sqlite3

import numpy as np

from core.config import MIN_SIMILARITY, TOP_K
from models.chunk import Chunk, ScoredChunk
from rag.embedding_service import blob_to_vector


class KnowledgeRetriever:
    """يجد المقاطع الأقرب دلاليًا للسؤال. القرب ليس صحة، والأقرب ليس بالضرورة كافيًا."""

    def __init__(self, conn: sqlite3.Connection, embedder, *,
                 top_k: int = TOP_K, min_similarity: float = MIN_SIMILARITY):
        self._conn = conn
        self._embedder = embedder
        self._top_k = top_k
        self._min_similarity = min_similarity

    def retrieve(self, query: str) -> list[ScoredChunk]:
        rows = self._load_rows()
        if not rows:
            return []   # لا حاجة لاستدعاء Ollama إن كانت القاعدة فارغة

        query_vec = np.asarray(self._embedder.embed(query), dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []
        query_unit = query_vec / query_norm

        kept, vectors = [], []
        for row in rows:
            vec = blob_to_vector(row["embedding"])
            norm = np.linalg.norm(vec)
            if vec.shape != query_unit.shape or norm == 0:
                continue   # بُعد مختلف أو متجه صفري: لا يمكن مقارنته
            kept.append(row)
            vectors.append(vec / norm)
        if not vectors:
            return []

        scores = np.vstack(vectors) @ query_unit          # cosine لكل المقاطع دفعة واحدة
        order = np.argsort(-scores, kind="stable")        # الأعلى أولًا، والتعادل بترتيب الإدخال

        results: list[ScoredChunk] = []
        for index in order:
            score = float(scores[index])
            if score < self._min_similarity:
                break
            row = kept[index]
            results.append(ScoredChunk(
                chunk=Chunk(id=row["id"], source=row["source"], text=row["text"],
                            title=row["title"], product_id=row["product_id"]),
                score=score,
            ))
            if len(results) == self._top_k:
                break
        return results

    def _load_rows(self) -> list[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute(
            "SELECT id, source, title, text, product_id, embedding FROM knowledge_chunks "
            "WHERE embedding IS NOT NULL AND embedding_model = ? ORDER BY id",
            (self._embedder.model,),
        )
        return cur.fetchall()
