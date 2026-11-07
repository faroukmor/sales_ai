"""GEANT conversational sales API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import get_chat_service
from app.schemas.chat_response import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.evidence_validator import EvidenceValidationError
from app.services.llm_service import (
    InvalidStructuredResponseError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.services.query_validator import QueryValidationError, UnsafeInputError

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse, summary="Chat with the GEANT sales assistant")
def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    try:
        return service.chat(request)
    except UnsafeInputError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The message contains unsupported instruction-override content",
        ) from None
    except QueryValidationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The request could not be understood safely",
        ) from None
    except (LLMAuthenticationError, LLMRateLimitError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The language service is temporarily unavailable",
        ) from None
    except LLMTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The language service timed out",
        ) from None
    except (
        LLMUnavailableError,
        InvalidStructuredResponseError,
        LLMServiceError,
        EvidenceValidationError,
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The assistant returned an unusable response",
        ) from None
    except (SQLAlchemyError, OSError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catalog service is unavailable",
        ) from None
