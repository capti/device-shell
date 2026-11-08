param(
    [string[]]$MutateTargets = @("app"),
    [switch]$SkipMutator = $false,
    [switch]$SkipCoverage = $false
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
$backendDir = Join-Path $repoRoot "backend"
$venvPy = Join-Path $backendDir ".venv\Scripts\python.exe"
$qaToolsVenv = Join-Path $repoRoot ".skills\ub-mode\.qa-tools-venv"
$qaPy = Join-Path $qaToolsVenv "Scripts\python.exe"
$qaSitePackages = Join-Path $qaToolsVenv "Lib\site-packages"

if (-not (Test-Path $venvPy)) {
    Write-Error "Backend venv python not found at $venvPy"
}
if (-not (Test-Path $qaPy)) {
    Write-Error "QA tools venv python not found at $qaPy"
}

if ((-not $SkipCoverage) -or (-not $SkipMutator)) {
    $loopbackCheck = @"
import socket, sys
lsock = socket.socket()
lsock.bind(('127.0.0.1', 0))
lsock.listen(1)
lsock.settimeout(1.0)
csock = socket.socket()
csock.setblocking(False)
try:
    csock.connect(lsock.getsockname())
except BlockingIOError:
    pass
try:
    s, _ = lsock.accept()
    s.close()
except Exception:
    sys.exit(1)
finally:
    csock.close()
    lsock.close()
"@

    & $venvPy -c $loopbackCheck
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Loopback TCP (127.0.0.1) is blocked (likely running inside the Windows no-network sandbox). Run this script with BypassSandbox: true so asyncio/TestClient socket.socketpair() does not deadlock."
        exit 1
    }
}

Push-Location $backendDir
try {
    Write-Host "=== [1/5] Running Ruff ===" -ForegroundColor Cyan
    & $venvPy -m ruff check .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (-not $SkipCoverage) {
        Write-Host "=== [2/5] Running Pytest + LCOV Coverage ===" -ForegroundColor Cyan
        $pytestTmp = Join-Path $backendDir "target\pytest_tmp"
        if (Test-Path $pytestTmp) { Remove-Item -Recurse -Force $pytestTmp -ErrorAction SilentlyContinue }

        $env:PYTHONPATH = $qaSitePackages
        & $venvPy -m coverage run --source=app -m pytest -q -o tmp_path_retention_policy=none --basetemp="target/pytest_tmp" -p no:cacheprovider
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        & $venvPy -m coverage lcov -o target/coverage/python/lcov.info
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
        if (Test-Path $pytestTmp) { Remove-Item -Recurse -Force $pytestTmp -ErrorAction SilentlyContinue }
    }

    Write-Host "=== [3/5] Running Crapper ===" -ForegroundColor Cyan
    & $qaPy -m crapper --use-existing-coverage
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== [4/5] Running Dryer ===" -ForegroundColor Cyan
    & $qaPy -m dryer app
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (-not $SkipMutator) {
        Write-Host "=== [5/5] Running Mutator ($($MutateTargets -join ', ')) ===" -ForegroundColor Cyan
        $testCmd = "`"$venvPy`" -m pytest -x -q -o tmp_path_retention_policy=none --basetemp=target/pytest_tmp -p no:cacheprovider"
        & $qaPy -m mutator --use-existing-coverage --test-command $testCmd @MutateTargets
        $mutExit = $LASTEXITCODE
        $pytestTmp = Join-Path $backendDir "target\pytest_tmp"
        if (Test-Path $pytestTmp) { Remove-Item -Recurse -Force $pytestTmp -ErrorAction SilentlyContinue }
        if ($mutExit -ne 0) { exit $mutExit }
    }

    Write-Host "=== All Uncle Bob checks passed! ===" -ForegroundColor Green
} finally {
    Pop-Location
}
