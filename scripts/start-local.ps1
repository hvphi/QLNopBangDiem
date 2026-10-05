$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$pythonBin = if ($env:PYTHON) { $env:PYTHON } else { Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' }
if (-not $env:APP_ENCRYPTION_KEY) {
    New-Item -ItemType Directory -Path '.local' -Force | Out-Null
    $keyPath = Join-Path $projectRoot '.local/encryption.key'
    if (-not (Test-Path -LiteralPath $keyPath)) {
        $randomKey = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
        [Convert]::ToHexString($randomKey) | Set-Content -LiteralPath $keyPath -NoNewline
    }
    $env:APP_ENCRYPTION_KEY = Get-Content -LiteralPath $keyPath -Raw
}
$env:APP_COOKIE_SECURE = 'false'
if (-not $env:APP_SIGNATURE_POLICY) { $env:APP_SIGNATURE_POLICY = 'local' }
& $pythonBin scripts/run.py serve
