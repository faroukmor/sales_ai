import os

import pytest

from app.core.config import get_settings
from app.services.intent_parser import IntentParser
from app.services.llm_service import LLMService

pytestmark = pytest.mark.groq_integration


def test_real_groq_structured_intent() -> None:
    if os.getenv("RUN_GROQ_INTEGRATION") != "1":
        pytest.skip("set RUN_GROQ_INTEGRATION=1 to enable real Groq inference")
    settings = get_settings()
    if settings.groq_api_key is None or not settings.groq_api_key.get_secret_value():
        pytest.skip("GROQ_API_KEY is not configured")

    result = IntentParser(
        LLMService.from_settings(settings),
        allow_powerful_fallback=settings.groq_allow_powerful_fallback,
    ).parse("Find a laptop under 100000 DZD with at least 16GB RAM")

    assert result.plan.intent == "product_search"
    assert result.plan.category == "laptop"
    assert result.plan.max_price == 100000
