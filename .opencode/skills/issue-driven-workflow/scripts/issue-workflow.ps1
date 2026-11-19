param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = $here
python -m issue_workflow @CliArgs
exit $LASTEXITCODE
