# core/exceptions.py
class GeantError(Exception):
    """الأصل المشترك لكل الأخطاء المتوقعة في التطبيق."""


class EmbeddingError(GeantError):
    """فشل توليد embedding (Ollama متوقف، نموذج غير موجود، رد غير صالح...)."""


class GenerationError(GeantError):
    """فشل توليد إجابة نصية من الـ LLM."""
