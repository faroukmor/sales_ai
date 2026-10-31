from functools import lru_cache

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.services.intent_parser import IntentParser
from app.services.llm_service import LLMConfigurationError, LLMService


@lru_cache
def get_intent_parser() -> IntentParser:
    """Build clients lazily on the first intent request, never at application startup."""

    settings = get_settings()
    try:
        service = LLMService.from_settings(settings)
    except LLMConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intent parsing service is not configured",
        ) from None
    return IntentParser(
        service,
        allow_powerful_fallback=settings.groq_allow_powerful_fallback,
        validation_debug=settings.intent_validation_debug,
    )
