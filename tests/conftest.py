import os

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# Configuration is intentionally required in production. Tests provide an isolated value
# before application modules are imported and never require a local .env file.
os.environ.setdefault("POSTGRES_PASSWORD", "unit-test-password")
os.environ.setdefault("APP_ENV", "test")

from app.db import models  # noqa: E402, F401
from app.db.database import Base  # noqa: E402


@pytest.fixture
def db_engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Session:
    with Session(db_engine) as session:
        yield session
