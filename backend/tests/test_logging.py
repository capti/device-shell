"""Структурные логи: JSON-формат, уровень и поля HTTP-запроса."""

import json
import logging
import sys
import time

from fastapi.testclient import TestClient

from app.logs import JsonFormatter, configure_logging
from app.main import app as fastapi_app
from app.middleware import _duration_ms


def _payload(level: int = logging.INFO, message: str = "hello", **extra) -> dict:
    record = logging.LogRecord(
        name="app.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(JsonFormatter().format(record))


def test_formatter_writes_single_json_record() -> None:
    payload = _payload(device_id=7)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["message"] == "hello"
    assert payload["device_id"] == 7
    assert payload["timestamp"].endswith("+00:00")
    # Служебные поля LogRecord не дублируются в JSON.
    assert "msg" not in payload
    assert "levelname" not in payload


def test_formatter_keeps_cyrillic_readable() -> None:
    record = logging.LogRecord(
        "app.test", logging.INFO, __file__, 1, "Привет", (), None
    )

    # Проверяем сырую строку: json.loads скрыл бы экранирование \uXXXX.
    assert "Привет" in JsonFormatter().format(record)


def test_formatter_keeps_traceback() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            "app.test", logging.ERROR, __file__, 1, "failed", (), sys.exc_info()
        )
        payload = json.loads(JsonFormatter().format(record))

    assert "ValueError" in payload["exception"]


def test_configure_logging_emits_json(capsys) -> None:
    configure_logging("INFO")
    logging.getLogger("app.check").info("probe", extra={"user": "e2e"})

    line = capsys.readouterr().err.strip().splitlines()[-1]

    payload = json.loads(line)
    assert payload["message"] == "probe"
    assert payload["user"] == "e2e"


def test_configure_logging_respects_level(capsys) -> None:
    configure_logging("WARNING")
    logging.getLogger("app.check").info("hidden")
    logging.getLogger("app.check").warning("shown")

    lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]

    assert [json.loads(line)["message"] for line in lines] == ["shown"]


def test_configure_logging_is_repeatable(capsys) -> None:
    configure_logging("INFO")
    configure_logging("INFO")
    logging.getLogger("app.check").info("once")

    lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]

    assert [json.loads(line)["message"] for line in lines] == ["once"]


def test_request_is_logged_with_fields(client: TestClient, caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/health")

    record = next(item for item in caplog.records if item.name == "app.request")
    assert record.getMessage() == "request"
    assert record.method == "GET"
    assert record.path == "/health"
    assert record.status_code == 200
    assert record.duration_ms >= 0


def test_duration_ms_converts_seconds_to_milliseconds(monkeypatch) -> None:
    ticks = iter([100.0, 100.25])
    monkeypatch.setattr(time, "perf_counter", lambda: next(ticks))

    assert _duration_ms(time.perf_counter()) == 250.0


def test_failed_request_logs_status(client: TestClient, caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/no-such-route")

    record = [item for item in caplog.records if item.name == "app.request"][-1]
    assert record.status_code == 404


def test_origin_rejection_is_logged(client: TestClient, caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.post(
            "/auth/login",
            json={"username": "nobody", "password": "secret123"},
            headers={"Origin": "https://evil.example"},
        )

    record = [item for item in caplog.records if item.name == "app.request"][-1]
    assert record.status_code == 403


def test_unhandled_error_is_logged_with_traceback(
    client: TestClient, caplog
) -> None:
    def boom() -> None:
        raise RuntimeError("boom")

    fastapi_app.add_api_route("/boom-test", boom, methods=["GET"])
    failing_client = TestClient(fastapi_app, raise_server_exceptions=False)
    try:
        with caplog.at_level(logging.INFO, logger="app.request"):
            response = failing_client.get("/boom-test")
    finally:
        fastapi_app.router.routes.pop()

    assert response.status_code == 500
    record = [item for item in caplog.records if item.name == "app.request"][-1]
    assert record.levelname == "ERROR"
    assert record.status_code == 500
    assert record.exc_info is not None


def test_request_log_does_not_contain_secrets(client: TestClient, caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.post(
            "/auth/login",
            json={"username": "nobody", "password": "super-secret-password"},
        )

    text = " ".join(str(item.__dict__) for item in caplog.records)

    assert "super-secret-password" not in text
    assert "authorization" not in text.lower()
