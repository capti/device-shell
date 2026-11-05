$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
if (-not $repoRoot) { $repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path }
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONPATH = "$repoRoot\backend"

$python = Join-Path $repoRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment python not found at $python"
}

& $python -m app.cli backup --keep 14
exit $LASTEXITCODE
