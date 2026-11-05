$ErrorActionPreference = 'Stop'

$gatusCommand = Get-Command gatus -CommandType Application -ErrorAction SilentlyContinue
if ($null -eq $gatusCommand) {
    throw 'Gatus is not installed or not on PATH. Install it with: go install github.com/TwiN/gatus/v5@latest'
}

$previousConfigPath = $env:GATUS_CONFIG_PATH
$previousLocation = Get-Location

try {
    Set-Location -LiteralPath $PSScriptRoot
    $env:GATUS_CONFIG_PATH = Join-Path $PSScriptRoot 'monitoring\gatus.yaml'
    & $gatusCommand.Source
    if ($LASTEXITCODE -ne 0) {
        throw "Gatus exited with code $LASTEXITCODE."
    }
}
finally {
    Set-Location -LiteralPath $previousLocation
    if ($null -eq $previousConfigPath) {
        Remove-Item Env:GATUS_CONFIG_PATH -ErrorAction SilentlyContinue
    }
    else {
        $env:GATUS_CONFIG_PATH = $previousConfigPath
    }
}
