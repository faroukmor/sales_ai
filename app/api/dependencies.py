import atexit
from functools import lru_cache
from threading import Lock
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.orm import Session

from app.agents.checkpoint import chat_checkpoint_serializer
from app.core.config import get_settings
from app.db.database import get_db
from app.services.chat_service import ChatService
from app.services.intent_parser import IntentParser
from app.services.llm_service import LLMConfigurationError, LLMService

_checkpoint_lock = Lock()
_checkpoint_context: Any = None
_checkpoint_saver: BaseCheckpointSaver | None = None


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


def get_chat_checkpointer() -> BaseCheckpointSaver:
    """Lazily open the production PostgreSQL checkpointer and create its tables."""

    global _checkpoint_context, _checkpoint_saver
    if _checkpoint_saver is not None:
        return _checkpoint_saver
    with _checkpoint_lock:
        if _checkpoint_saver is not None:
            return _checkpoint_saver
        uri = get_settings().checkpoint_database_uri.replace("postgresql+psycopg://", "postgresql://")
        try:
            context = PostgresSaver.from_conn_string(uri)
            saver = context.__enter__()
            saver.serde = chat_checkpoint_serializer()
            saver.setup()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Conversation persistence is unavailable",
            ) from None
        _checkpoint_context = context
        _checkpoint_saver = saver
        return saver


def _close_checkpointer() -> None:
    global _checkpoint_context, _checkpoint_saver
    if _checkpoint_context is not None:
        _checkpoint_context.__exit__(None, None, None)
    _checkpoint_context = None
    _checkpoint_saver = None


atexit.register(_close_checkpointer)


def get_chat_service(
    database: Annotated[Session, Depends(get_db)],
    parser: Annotated[IntentParser, Depends(get_intent_parser)],
    checkpointer: Annotated[BaseCheckpointSaver, Depends(get_chat_checkpointer)],
) -> ChatService:
    return ChatService(
        database,
        parser,
        checkpointer,
        max_history_messages=get_settings().chat_max_history_messages,
    )
