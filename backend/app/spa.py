"""Раздача собранного SPA с того же порта, что и API (однопортовый production).

Маршруты API регистрируются в приложении вперемешку с тестовыми и служебными,
поэтому вместо catch-all маршрута используется обработчик 404: он срабатывает,
только когда маршрут не совпал (или маршрут сам ответил 404), и не зависит от
порядка регистрации.

Отдаются настоящие файлы сборки, а на навигацию браузера — index.html. Клиент
с `Accept: application/json` (фронтенд) или `*/*` на неизвестный путь получает
обычный JSON-404 `{code, message}`.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.errors import http_exception_response

# Бандлы Vite содержат хеш в имени: кэшируем навсегда, index.html — никогда.
_ASSET_CACHE = {"Cache-Control": "public, max-age=31536000, immutable"}
_INDEX_CACHE = {"Cache-Control": "no-cache"}


def resolve_file(dist: Path, relative: str) -> Path | None:
    """Файл из каталога сборки, если он существует и путь не выходит за его пределы."""
    if not relative:
        return None
    candidate = (dist / relative).resolve()
    if not candidate.is_relative_to(dist.resolve()):
        return None
    return candidate if candidate.is_file() else None


def spa_response(request: Request, relative: str) -> Response | None:
    """Файл сборки или index.html; `None`, если отвечать нечем."""
    dist = settings.frontend_dist
    if not dist.is_dir():
        return None

    file = resolve_file(dist, relative)
    if file is not None:
        headers = _ASSET_CACHE if relative.startswith("assets/") else None
        return FileResponse(file, headers=headers)

    index = dist / "index.html"
    if not index.is_file():
        return None
    accepts_html = "text/html" in request.headers.get("accept", "").lower()
    if relative == "" or accepts_html:
        return FileResponse(index, headers=_INDEX_CACHE)
    return None


def register_spa(app: FastAPI) -> None:
    """На 404 отдавать SPA, когда запрос сделан браузером и сборка существует."""

    @app.exception_handler(StarletteHTTPException)
    async def spa_handler(request: Request, exc: StarletteHTTPException) -> Response:
        if exc.status_code == 404:
            response = spa_response(request, request.url.path.lstrip("/"))
            if response is not None:
                return response
        return http_exception_response(exc)
