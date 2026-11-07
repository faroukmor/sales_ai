import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.intent import router as intent_router
from app.api.routes.storefront import router as storefront_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.database import check_database_connection

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.include_router(intent_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(storefront_router)


class HealthResponse(BaseModel):
    status: str
    service: str


class DatabaseHealthResponse(BaseModel):
    database: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@app.get("/health/db", response_model=DatabaseHealthResponse)
def database_health() -> DatabaseHealthResponse:
    try:
        check_database_connection()
    except (SQLAlchemyError, OSError):
        logger.warning("Database health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from None
    return DatabaseHealthResponse(database="connected")
