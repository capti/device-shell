"""Единый конверт ошибок API: `{"code": ..., "message": ...}`."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Ожидаемая ошибка бизнес-логики с кодом для фронтенда."""

    def __init__(self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


_DEFAULT_CODES = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    422: "VALIDATION_ERROR",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
}

_DEFAULT_MESSAGES = {
    status.HTTP_400_BAD_REQUEST: "Некорректный запрос",
    status.HTTP_401_UNAUTHORIZED: "Требуется вход в систему",
    status.HTTP_403_FORBIDDEN: "Недостаточно прав",
    status.HTTP_404_NOT_FOUND: "Запрос не найден",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Метод не поддерживается",
    status.HTTP_409_CONFLICT: "Конфликт данных",
    422: "Некорректные данные запроса",
    status.HTTP_429_TOO_MANY_REQUESTS: "Слишком много запросов",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Внутренняя ошибка сервера",
}


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "message": message})


def http_exception_response(exc: StarletteHTTPException) -> JSONResponse:
    """Конверт для HTTPException: detail становится сообщением, иначе — текст по умолчанию."""
    code = _DEFAULT_CODES.get(exc.status_code, "ERROR")
    default_message = _DEFAULT_MESSAGES.get(exc.status_code, "Ошибка")
    detail = exc.detail
    message = detail if isinstance(detail, str) and detail else default_message
    return error_response(exc.status_code, code, message)


def _validation_message(exc: RequestValidationError) -> str:
    fields: list[str] = []
    for error in exc.errors():
        location = [
            str(part)
            for part in error.get("loc", ())
            if part not in ("body", "query", "path")
        ]
        fields.append(".".join(location) or "body")
    unique_fields = list(dict.fromkeys(fields))
    if not unique_fields:
        return _DEFAULT_MESSAGES[status.HTTP_422_UNPROCESSABLE_ENTITY]
    return f"Некорректные данные: {', '.join(unique_fields)}"


def register_exception_handlers(app: FastAPI) -> None:
    """Приводит все ошибки к одному формату `{code, message}`."""

    @app.exception_handler(AppError)
    async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return http_exception_response(exc)

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Необработанная ошибка: %s %s", request.method, request.url.path, exc_info=exc
        )
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            _DEFAULT_CODES[status.HTTP_500_INTERNAL_SERVER_ERROR],
            _DEFAULT_MESSAGES[status.HTTP_500_INTERNAL_SERVER_ERROR],
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        message = _validation_message(exc)
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            _DEFAULT_CODES[status.HTTP_422_UNPROCESSABLE_ENTITY],
            message,
        )
