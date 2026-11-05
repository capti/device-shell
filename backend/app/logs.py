"""Структурные логи: одна JSON-строка на запись лога.

Формат рассчитан на чтение глазами и на разбор машиной: `timestamp`, `level`,
`logger`, `message` плюс любые поля, переданные через `extra` (например,
`method`, `path`, `status_code`, `duration_ms`). Секреты в лог не попадают:
ни тела запроса, ни cookie, ни заголовков авторизации никто не передаёт.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.config import settings

# Поля, которые logging добавляет сам: они не должны попадать в JSON как есть.
_RESERVED = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)

_handler: logging.Handler | None = None


class JsonFormatter(logging.Formatter):
    """Форматирует запись как одну JSON-строку."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str | None = None) -> None:
    """Переводит корневой логгер на JSON; повторный вызов не дублирует вывод."""
    global _handler
    root = logging.getLogger()
    if _handler is not None:
        root.removeHandler(_handler)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level or settings.log_level)
    _handler = handler
