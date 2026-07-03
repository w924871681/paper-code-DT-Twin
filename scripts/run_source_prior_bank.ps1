param([string]$PythonExe="python", [Parameter(ValueFromRemainingArguments=$true)][string[]]$ExtraArgs)
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
Set-Location $Root
& $PythonExe (Join-Path $PSScriptRoot "preflight_source_prior_bank.py") @ExtraArgs
if($LASTEXITCODE -ne 0){throw "Command failed with exit code $LASTEXITCODE"}
