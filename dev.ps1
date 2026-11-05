# Запуск backend в режиме разработки.
# Один процесс uvicorn: SQLite и rate limit в памяти не рассчитаны на несколько воркеров.
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "backend")

# Браузер открывает сайт на :5173 (Vite dev-сервер), поэтому мутации приходят
# с этим Origin — иначе проверка Origin отклонит их как 403.
$env:APP_BASE_URL = "http://localhost:5173"

# uv может быть не в PATH, если установлен через pip --user.
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    uv run uvicorn app.main:app --reload --port 8000
}
else {
    python -m uv run uvicorn app.main:app --reload --port 8000
}
