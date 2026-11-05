from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from app import __version__
from app.config import settings
from app.db import engine
from app.main import create_app


def _break_db(
    _conn,
    _cursor,
    _statement,
    _parameters,
    _context,
    _executemany,
) -> None:
    """Падаем на уровне движка, чтобы сработала ветка `except` в `_db_ok()`."""
    raise OperationalError("SELECT 1", {}, Exception("нет соединения с БД"))


@pytest.fixture()
def broken_database() -> Iterator[None]:
    """Любой запрос к БД падает; после теста соединение восстанавливается."""
    event.listen(engine, "before_cursor_execute", _break_db)
    try:
        yield
    finally:
        event.remove(engine, "before_cursor_execute", _break_db)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ok",
        "version": __version__,
        "database": "ok",
    }


def test_health_returns_503_when_db_is_unavailable(
    client: TestClient, broken_database: None
) -> None:
    """При падении БД эндпоинт возвращает 503 и однозначный JSON, а не общий конверт ошибок."""
    response = client.get("/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload == {
        "status": "degraded",
        "version": __version__,
        "database": "error",
    }


def test_health_recovers_after_db_failure(client: TestClient) -> None:
    """Падение БД в одном запросе не ломает последующие."""
    event.listen(engine, "before_cursor_execute", _break_db)
    try:
        assert client.get("/health").status_code == 503
    finally:
        event.remove(engine, "before_cursor_execute", _break_db)

    assert client.get("/health").status_code == 200


def test_create_app_is_repeatable_when_media_dir_exists() -> None:
    """Фабрику вызывают повторно (тесты, reload), когда каталог media уже есть."""
    settings.media_dir.mkdir(parents=True, exist_ok=True)

    create_app()
    create_app()
