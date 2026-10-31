import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Format standard log records as one-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in (
            "code",
            "field_path",
            "reason",
            "expected",
            "model_used",
            "latency_ms",
            "token_usage",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_level: str) -> None:
    """Configure the root logger idempotently for development reloads."""

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    handler = next(
        (item for item in root_logger.handlers if getattr(item, "_sales_ai_handler", False)),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler()
        handler._sales_ai_handler = True  # type: ignore[attr-defined]
        root_logger.addHandler(handler)
    handler.setFormatter(JsonFormatter())
    handler.setLevel(log_level)
