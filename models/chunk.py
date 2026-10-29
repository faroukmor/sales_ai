# models/chunk.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    """مقطع نصي من قاعدة المعرفة."""
    id: int
    source: str
    text: str
    title: str | None = None
    product_id: int | None = None


@dataclass(frozen=True)
class ScoredChunk:
    """مقطع مع درجة صلته بالسؤال (الصلة ليست صحة)."""
    chunk: Chunk
    score: float
