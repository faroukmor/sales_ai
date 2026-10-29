# rag/knowledge_ingestor.py
import re
import sqlite3
from pathlib import Path

from core.config import MAX_CHUNK_CHARS
from rag.embedding_service import vector_to_blob


def split_paragraphs(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """يقسّم النص إلى مقاطع: فقرة لكل مقطع، والفقرة الطويلة تُقطَّع عند أقرب مسافة."""
    chunks: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = " ".join(paragraph.split())
        while len(paragraph) > max_chars:
            cut = paragraph.rfind(" ", 0, max_chars)
            if cut <= 0:
                cut = max_chars
            chunks.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        if paragraph:
            chunks.append(paragraph)
    return chunks


class KnowledgeIngestor:
    """الجانب الكتابي لقاعدة المعرفة (الـ retriever للقراءة فقط)."""

    def __init__(self, conn: sqlite3.Connection, embedder):
        self._conn = conn
        self._embedder = embedder

    def add_document(
        self, source: str, text: str, *, title: str | None = None,
        product_id: int | None = None,
    ) -> int:
        """يستبدل كل مقاطع هذا المصدر بمقاطع النص الجديد. يرجع عدد المقاطع."""
        pieces = split_paragraphs(text)
        # نولّد كل المتجهات أولًا: إن فشل Ollama لا نكون قد غيّرنا شيئًا في القاعدة.
        vectors = [self._embedder.embed(piece) for piece in pieces]
        with self._conn:  # معاملة واحدة: حذف القديم + إدخال الجديد معًا أو لا شيء
            self._conn.execute("DELETE FROM knowledge_chunks WHERE source = ?", (source,))
            for piece, vector in zip(pieces, vectors):
                self._conn.execute(
                    "INSERT INTO knowledge_chunks "
                    "(source, title, text, product_id, embedding, embedding_model) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (source, title, piece, product_id,
                     vector_to_blob(vector), self._embedder.model),
                )
        return len(pieces)

    def add_directory(self, folder: Path) -> dict[str, int]:
        """يدخل كل ملفات .txt و .md في المجلد. يرجع {اسم الملف: عدد المقاطع}."""
        report: dict[str, int] = {}
        for path in sorted(Path(folder).iterdir()):
            if path.is_file() and path.suffix.lower() in {".txt", ".md"}:
                text = path.read_text(encoding="utf-8")
                report[path.name] = self.add_document(path.name, text, title=path.stem)
        return report
