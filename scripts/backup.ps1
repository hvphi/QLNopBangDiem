param([Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$pythonBin = if ($env:PYTHON) { $env:PYTHON } else { Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' }
$dataRoot = if ($env:APP_DATA_DIR) { $env:APP_DATA_DIR } else { 'runtime' }
$snapshot = Join-Path $Destination (Get-Date -Format 'yyyyMMdd-HHmmss')
& $pythonBin scripts/run.py backend.operations backup $dataRoot $snapshot
if ($LASTEXITCODE -ne 0) { throw 'Backup thất bại' }
