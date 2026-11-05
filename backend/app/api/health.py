"""Служебные эндпоинты."""

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app import __version__
from app.db import SessionLocal

router = APIRouter(tags=["system"])

DEGRADED_PAYLOAD = {
    "status": "degraded",
    "version": __version__,
    "database": "error",
}


class HealthStatus(BaseModel):
    """Ответ `/health`: живость приложения и доступность БД.

    Описывает оба исхода — 200 и 503: сам ответ отдаётся напрямую через
    JSONResponse, поэтому модель нужна только для документации в OpenAPI.
    """

    status: Literal["ok", "degraded"]
    version: str
    database: Literal["ok", "error"]


def _db_ok() -> bool:
    """Проверка доступности БД."""
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@router.get(
    "/health",
    response_model=None,
    responses={
        200: {"model": HealthStatus, "description": "Приложение и БД в порядке"},
        503: {"model": HealthStatus, "description": "БД недоступна"},
    },
)
def health() -> dict[str, object] | JSONResponse:
    """Проверка живости приложения и доступности БД.

    Отказ БД отдаётся напрямую через JSONResponse, а не через HTTPException:
    глобальный обработчик ошибок превращает detail в конверт {code, message},
    а мониторингу нужны явные маркеры "degraded" и "error".
    """
    if _db_ok():
        return {
            "status": "ok",
            "version": __version__,
            "database": "ok",
        }
    return JSONResponse(status_code=503, content=DEGRADED_PAYLOAD)
