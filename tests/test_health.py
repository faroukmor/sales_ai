from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Sales AI 2.0"}


def test_database_health_success() -> None:
    with patch("app.main.check_database_connection", return_value=True):
        response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"database": "connected"}


def test_database_health_failure() -> None:
    error = OperationalError("SELECT 1", {}, OSError("connection refused"))
    with patch("app.main.check_database_connection", side_effect=error):
        response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
    assert "connection refused" not in response.text

