import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from app.core.config import Settings


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Configured Sales AI")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Configured Sales AI"
    assert settings.groq_api_key is None
    assert settings.postgres_password.get_secret_value() == "secret"
    assert settings.groq_model_fast == "openai/gpt-oss-20b"
    assert settings.groq_model_powerful == "openai/gpt-oss-120b"
    assert settings.groq_reasoning_effort_fast == "low"
    assert settings.groq_reasoning_effort_powerful == "medium"


def test_database_url_handles_special_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss:/word")

    settings = Settings(_env_file=None)
    rendered = settings.database_url.render_as_string(hide_password=False)

    assert rendered == (
        "postgresql+psycopg://sales_ai:p%40ss%3A%2Fword@127.0.0.1:55432/sales_ai"
    )
    assert "p@ss:/word" not in rendered


def test_missing_database_password_is_clear_and_does_not_echo_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    class IsolatedSettings(Settings):
        model_config = SettingsConfigDict(env_file=None, extra="ignore")

    with pytest.raises(ValidationError) as error:
        IsolatedSettings()  # type: ignore[call-arg]

    message = str(error.value)
    assert "postgres_password" in message
    assert "unit-test-password" not in message
