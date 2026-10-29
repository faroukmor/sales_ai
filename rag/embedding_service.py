# rag/embedding_service.py
import numpy as np

from core.config import EMBED_MODEL, OLLAMA_HOST, OLLAMA_TIMEOUT_SECONDS
from core.exceptions import EmbeddingError


def vector_to_blob(vector) -> bytes:
    """يحوّل المتجه إلى bytes (float32) للتخزين في عمود BLOB."""
    return np.asarray(vector, dtype=np.float32).tobytes()


def blob_to_vector(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


class EmbeddingService:
    """المكان الوحيد الذي يتحدث مع Ollama لتوليد embeddings."""

    def __init__(self, client=None, model: str = EMBED_MODEL):
        if client is None:
            import ollama  # استيراد متأخر: الاختبارات بعميل وهمي لا تحتاج المكتبة
            client = ollama.Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT_SECONDS)
        self._client = client
        self.model = model

    def embed(self, text: str) -> np.ndarray:
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        try:
            result = self._client.embed(model=self.model, input=text)
            vector = result["embeddings"][0]
        except Exception as exc:  # أخطاء النقل متعددة الأنواع؛ نوحّدها في خطأ واحد
            raise EmbeddingError(
                f"Could not get an embedding (model={self.model}): {exc}"
            ) from exc
        array = np.asarray(vector, dtype=np.float32)
        if array.ndim != 1 or array.size == 0:
            raise EmbeddingError("Ollama returned an invalid embedding")
        return array
