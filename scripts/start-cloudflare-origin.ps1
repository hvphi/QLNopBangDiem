param(
    [ValidateRange(1024,65535)][int]$Port = 8001,
    [ValidateSet('strict','local')][string]$SignaturePolicy = 'strict'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$pythonBin = if ($env:PYTHON) { $env:PYTHON } else { Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' }
if (-not $env:APP_ENCRYPTION_KEY) {
    $keyPath = Join-Path $projectRoot '.local/encryption.key'
    if (-not (Test-Path -LiteralPath $keyPath)) {
        throw 'Set APP_ENCRYPTION_KEY from your secret store, or provide the existing .local/encryption.key. Do not generate a different key for existing data.'
    }
    $env:APP_ENCRYPTION_KEY = (Get-Content -LiteralPath $keyPath -Raw).Trim()
}
if ($env:APP_ENCRYPTION_KEY -notmatch '^[a-fA-F0-9]{64}$') { throw 'APP_ENCRYPTION_KEY must be 64 hex characters.' }
$env:APP_COOKIE_SECURE = 'true'
$env:APP_SIGNATURE_POLICY = $SignaturePolicy
& $pythonBin scripts/run.py uvicorn backend.app:create_app --factory --host 127.0.0.1 --port $Port --proxy-headers --forwarded-allow-ips '127.0.0.1,::1'
if ($LASTEXITCODE -ne 0) { throw "Origin server exited with code $LASTEXITCODE" }
