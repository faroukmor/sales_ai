from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_intent_parser
from app.core.config import get_settings
from app.schemas.intent import IntentFiltersResponse, IntentParseRequest, IntentParseResponse
from app.services.intent_parser import IntentParser
from app.services.llm_service import (
    InvalidStructuredResponseError,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.services.query_validator import QueryValidationError, UnsafeInputError

router = APIRouter(prefix="/api/intent", tags=["intent"])


@router.post(
    "/parse",
    response_model=IntentParseResponse,
    summary="Parse a multilingual customer message",
    description=(
        "Returns an intent and normalized filters. It does not query products, execute SQL, "
        "or perform a recommendation. Keep disabled in exposed environments until "
        "authentication and rate limiting are added."
    ),
)
def parse_intent(
    request: IntentParseRequest,
    parser: Annotated[IntentParser, Depends(get_intent_parser)],
) -> IntentParseResponse:
    if not get_settings().intent_api_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        result = parser.parse(request.message)
    except UnsafeInputError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The message contains unsupported instruction-override content",
        ) from None
    except QueryValidationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The parsed request could not be validated",
        ) from None
    except LLMConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intent parsing service is not configured",
        ) from None
    except LLMAuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intent parsing service authentication failed",
        ) from None
    except LLMRateLimitError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intent parsing service is rate limited",
        ) from None
    except LLMTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Intent parsing service timed out",
        ) from None
    except (LLMUnavailableError, InvalidStructuredResponseError, LLMServiceError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Intent parsing service returned an unusable response",
        ) from None

    plan = result.plan
    return IntentParseResponse(
        original_message=plan.original_message,
        intent=plan.intent,
        language=plan.language,
        filters=IntentFiltersResponse(
            category=plan.category,
            brand=plan.brand,
            min_price=plan.min_price,
            max_price=plan.max_price,
            currency=plan.currency,
            in_stock_only=plan.in_stock_only,
            specification_constraints=plan.specification_constraints,
        ),
        product_refs=plan.product_refs,
        needs_clarification=plan.needs_clarification,
        missing_info=plan.missing_info,
        clarification_question=plan.clarification_question,
        model_used=result.model_used,
        escalated=result.escalated,
        latency_ms=result.latency_ms,
        token_usage=result.token_usage,
    )
