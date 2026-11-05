"""Middleware: проверка Origin на мутациях и структурные логи запросов."""

import logging
import time
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.errors import error_response

MUTATING_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})

request_logger = logging.getLogger("app.request")


def _duration_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


def _url_origin(value: str) -> tuple[str, str]:
    parts = urlsplit(value.strip())
    return parts.scheme.lower(), parts.netloc.lower()


def is_allowed_origin(origin: str) -> bool:
    """Совпадает ли Origin с адресом приложения (схема + хост + порт)."""
    return _url_origin(origin) == _url_origin(settings.app_base_url)


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Отклоняет мутации с чужим Origin.

    В production запрос без Origin тоже отклоняется: браузер всегда отправляет
    его на мутации, а не-браузерный клиент должен сам указать Origin.
    В dev и test запросы без Origin пропускаются: SameSite=Lax закрывает
    основную часть CSRF, а локальные curl и тесты не должны ломаться.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in MUTATING_METHODS:
            origin = request.headers.get("origin")
            if origin is None:
                if settings.is_production:
                    return error_response(
                        403, "FORBIDDEN", "Недопустимый источник запроса"
                    )
            elif not is_allowed_origin(origin):
                return error_response(403, "FORBIDDEN", "Недопустимый источник запроса")
        return await call_next(request)


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Пишет по строке на запрос: метод, путь, статус и длительность.

    Тело запроса, cookie и заголовки не логируются — только то, что нужно,
    чтобы разобрать инцидент, без риска утечь паролю или токену сессии.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            request_logger.exception(
                "request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": _duration_ms(started),
                },
            )
            raise
        request_logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": _duration_ms(started),
            },
        )
        return response
