# syntax=docker/dockerfile:1
# Один контейнер: SPA собирается на Node, backend ставится через uv,
# FastAPI раздаёт API, /media и frontend/dist с одного порта.

# --- Сборка фронтенда ---
# Node 26 — версия, на которой проверена сборка фронтенда этой реплики;
# этап одноразовый, в итоговый образ он не попадает.
FROM node:26-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Backend и итоговый образ ---
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH

# tzdata нужен, чтобы TZ задавал локальный пояс: просрочка и границы отчётов
# считаются по локальной дате сервера (см. app/clock.py).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
# Сначала только манифесты: слой с зависимостями пересобирается лишь при
# изменении pyproject.toml или uv.lock.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
# Сборка SPA из этапа frontend: её раздаёт FastAPI (см. app/spa.py).
COPY --from=frontend /src/dist /app/frontend/dist

# Данные (БД, фото, бэкапи) живут в /app/data и монтируются с хоста.
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin qa \
    && mkdir -p /app/data \
    && chown -R qa:qa /app
USER qa

ENV APP_ENV=production \
    APP_BASE_URL=http://localhost:8000 \
    COOKIE_SECURE=false \
    HOST=0.0.0.0 \
    PORT=8000 \
    ADMIN_USERNAME=admin \
    ADMIN_FULL_NAME=Администратор

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c 'import os, urllib.request as u; u.urlopen("http://127.0.0.1:%s/health" % os.environ.get("PORT", "8000"), timeout=4)'

# Миграции, администратор из окружения, затем один процесс uvicorn.
CMD ["python", "-m", "app.entrypoint"]
