# Запуск проекта в разработке: backend (:8000) и Vite dev-сервер (:5173) в одном
# окне. Оба с горячей перезагрузкой, Ctrl+C останавливает обоих.
# Один процесс backend на воркер: SQLite и rate limit в памяти не рассчитаны
# на несколько воркеров.
param(
    # Только backend, без Vite dev-сервера.
    [switch]$BackendOnly,
    # Не открывать браузер на localhost:5173.
    [switch]$NoBrowser
)
$ErrorActionPreference = "Stop"

$frontendDir = Join-Path $PSScriptRoot "frontend"
Set-Location (Join-Path $PSScriptRoot "backend")

# Браузер открывает сайт на :5173 (Vite dev-сервер), поэтому мутации приходят
# с этим Origin — иначе проверка Origin отклонит их как 403.
$env:APP_BASE_URL = "http://localhost:5173"

# Останавливает процесс вместе с детьми: у uvicorn --reload дочерний процесс
# иначе переживёт родителя и продолжит держать :8000.
function Stop-ProcessTree($Process) {
    if (-not $Process -or $Process.HasExited) { return }
    # cmd проглатывает вывод taskkill, иначе $ErrorActionPreference = "Stop"
    # прервёт скрипт на сообщении «процесс уже завершён».
    & cmd /c "taskkill /PID $($Process.Id) /T /F >nul 2>&1"
}

# uv может быть не в PATH, если установлен через pip --user.
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv -and $uv.CommandType -ne "Application") { $uv = $null }
if ($uv) {
    $backendFile = $uv.Path
    $backendArgs = @("run", "uvicorn", "app.main:app", "--reload", "--port", "8000")
}
else {
    $backendFile = "python"
    $backendArgs = @("-m", "uv", "run", "uvicorn", "app.main:app", "--reload", "--port", "8000")
}

$children = @()

try {
    if (-not $BackendOnly) {
        # Проверяем до запуска: без node_modules Vite не поднимется, а backend
        # пришлось бы останавливать вручную.
        # Get-Command npm возвращает npm.ps1, а Start-Process запускает только
        # исполняемые файлы, поэтому запрашиваем npm.cmd явно.
        $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if (-not $npm) {
            throw "npm не найден: установите Node.js."
        }
        if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
            throw "frontend/node_modules не найден: выполните npm install в frontend/."
        }
    }

    Write-Host "backend  :8000  uvicorn --reload"
    $children += Start-Process -FilePath $backendFile -ArgumentList $backendArgs `
        -NoNewWindow -PassThru

    $vite = $null
    if (-not $BackendOnly) {
        Write-Host "frontend :5173  vite (HMR)"
        $vite = Start-Process -FilePath $npm.Path -ArgumentList @("run", "dev") `
            -WorkingDirectory $frontendDir -NoNewWindow -PassThru
        $children += $vite

        if (-not $NoBrowser) {
            # Ждём, пока поднимутся и Vite, и backend: иначе первый запрос
            # браузера уйдёт в прокси и получит ECONNREFUSED. Backend слушает
            # только IPv4, поэтому health проверяем по 127.0.0.1 — иначе
            # каждая попытка ждёт таймаут на ::1.
            $ready = $false
            for ($try = 0; $try -lt 40 -and -not $vite.HasExited; $try++) {
                try {
                    Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 1 | Out-Null
                    Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 1 | Out-Null
                    $ready = $true
                    break
                }
                catch {
                    Start-Sleep -Milliseconds 500
                }
            }
            if (-not $ready) {
                Write-Warning "Стек не поднялся: Vite или backend не ответили за 20 с."
            }
            else {
                # Отсутствие браузера по умолчанию не должно гасить стек.
                try {
                    Start-Process "http://localhost:5173"
                }
                catch {
                    Write-Warning "Браузер не открылся: $($_.Exception.Message)"
                }
            }
        }
    }

    # Ждём, пока завершится хотя бы один процесс: падение одного гасит второй.
    while (-not ($children | Where-Object { $_.HasExited } | Select-Object -First 1)) {
        Start-Sleep -Milliseconds 250
    }
}
finally {
    $children | ForEach-Object { Stop-ProcessTree $_ }
}
