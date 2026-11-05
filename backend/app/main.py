"""Фабрика FastAPI-приложения."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.devices import router as devices_router
from app.api.health import router as health_router
from app.api.maintenance import router as maintenance_router
from app.api.notifications import router as notifications_router
from app.api.photos import router as photos_router
from app.api.reports import router as reports_router
from app.api.rotation import router as rotation_router
from app.api.users import router as users_router
from app.config import settings
from app.errors import register_exception_handlers
from app.logs import configure_logging
from app.middleware import OriginCheckMiddleware, RequestLogMiddleware
from app.spa import register_spa


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="QA Test Staff API",
        version=__version__,
        description="Сайт для учёта тестовых смартфонов",
    )
    register_exception_handlers(app)
    # Порядок важен: последний добавленный middleware — внешний, поэтому
    # отказы Origin (403) тоже попадают в лог запросов.
    app.add_middleware(OriginCheckMiddleware)
    app.add_middleware(RequestLogMiddleware)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(devices_router)
    app.include_router(rotation_router)
    app.include_router(maintenance_router)
    app.include_router(notifications_router)
    app.include_router(photos_router)
    app.include_router(reports_router)
    app.include_router(audit_router)
    # Файлы фото отдаются без сессии (решение зафиксировано в design.md).
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")
    # SPA подменяет 404 на index.html; регистрируется после обработчиков ошибок,
    # чтобы переопределить их обработчик HTTPException в свою пользу.
    register_spa(app)
    return app


app = create_app()
