$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Review credentials before production."
}

Write-Host "Starting MultiCam Re-ID API on http://127.0.0.1:8000"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000