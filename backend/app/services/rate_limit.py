"""Rate limit попыток входа в память процесса.

Скользящее окно по ключу `ip + username`: не более N неудачных попыток за окно,
после чего ключ блокируется на 15 минут. Состояние сбрасывается при рестарте —
для одного локального процесса это приемлемо (design.md, решение 7).
"""

import threading
from datetime import datetime, timedelta

from app.clock import now_local
from app.config import settings
from app.errors import AppError


class LoginRateLimiter:
    def __init__(
        self,
        max_attempts: int = 5,
        window: timedelta = timedelta(minutes=1),
        lockout: timedelta = timedelta(minutes=15),
    ) -> None:
        self._max_attempts = max_attempts
        self._window = window
        self._lockout = lockout
        self._failures: dict[str, list[datetime]] = {}
        self._blocked_until: dict[str, datetime] = {}
        self._lockout_minutes = max(1, int(lockout.total_seconds() // 60))
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Бросает 429, если ключ заблокирован."""
        with self._lock:
            blocked_until = self._blocked_until.get(key)
            if blocked_until is None:
                return
            if blocked_until > now_local():
                raise AppError(
                    "RATE_LIMITED",
                    "Слишком много попыток входа. "
                    f"Повторите через {self._lockout_minutes} мин.",
                    429,
                )
            self._blocked_until.pop(key, None)

    def register_failure(self, key: str) -> None:
        """Учитывает неудачную попытку и при превышении лимита блокирует ключ."""
        now = now_local()
        with self._lock:
            attempts = [
                moment
                for moment in self._failures.get(key, [])
                if now - moment < self._window
            ]
            attempts.append(now)
            if len(attempts) >= self._max_attempts:
                self._blocked_until[key] = now + self._lockout
                self._failures.pop(key, None)
                return
            self._failures[key] = attempts

    def reset(self, key: str) -> None:
        """Успешный вход очищает историю неудач."""
        with self._lock:
            self._failures.pop(key, None)
            self._blocked_until.pop(key, None)

    def clear(self) -> None:
        """Полный сброс состояния (тесты, рестарт)."""
        with self._lock:
            self._failures.clear()
            self._blocked_until.clear()


login_rate_limiter = LoginRateLimiter(
    max_attempts=settings.login_rate_limit_attempts,
    window=timedelta(seconds=settings.login_rate_limit_window_seconds),
    lockout=timedelta(minutes=settings.login_lockout_minutes),
)
