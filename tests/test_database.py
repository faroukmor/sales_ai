from unittest.mock import Mock, patch

from app.db.database import get_db


def test_database_session_is_closed() -> None:
    session = Mock()
    with patch("app.db.database.SessionLocal", return_value=session):
        dependency = get_db()
        assert next(dependency) is session
        dependency.close()

    session.close.assert_called_once_with()


def test_application_imports() -> None:
    from app.main import app

    assert app.title == "Sales AI 2.0"
    assert app.version == "0.1.0"

