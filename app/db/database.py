from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for ORM models introduced in future phases."""


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped session and always release its resources."""

    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


def check_database_connection(database_engine: Engine = engine) -> bool:
    """Check connectivity without leaking connection details to callers."""

    with database_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True

