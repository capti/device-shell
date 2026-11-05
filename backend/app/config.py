"""Настройки приложения из переменных окружения и `.env`."""

from datetime import timedelta
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Настройки backend.

    Все значения можно переопределить переменными окружения с теми же именами
    в верхнем регистре (`DATABASE_URL`, `COOKIE_SECURE`, ...).
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"

    # По умолчанию SQLite лежит рядом с backend, в data/qa.db.
    database_url: str = f"sqlite:///{(PROJECT_DIR / 'data' / 'qa.db').as_posix()}"
    data_dir: Path = PROJECT_DIR / "data"

    session_ttl_days: int = 7
    cookie_secure: bool = False

    # Уровень структурных логов: DEBUG, INFO, WARNING, ERROR.
    log_level: str = "INFO"

    # Каталог собранного SPA: FastAPI раздаёт его с того же порта, что и API.
    # В dev его обычно нет — фронтенд поднимает Vite на :5173.
    frontend_dist: Path = PROJECT_DIR / "frontend" / "dist"

    session_cookie_name: str = "qa_session"
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 60
    login_lockout_minutes: int = 15

    @property
    def media_dir(self) -> Path:
        """Каталог файлов фото: `data/media/` (файлы бэкапятся вместе с БД)."""
        return self.data_dir / "media"

    @property
    def backup_dir(self) -> Path:
        """Каталог резервных копий: `data/backups/` рядом с базой и media."""
        return self.data_dir / "backups"

    @property
    def session_ttl(self) -> timedelta:
        return timedelta(days=self.session_ttl_days)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


settings = Settings()
