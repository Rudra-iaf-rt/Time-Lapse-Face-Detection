$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Starting Docker infrastructure..."
docker compose -f docker/docker-compose.yml up -d

Write-Host "Synchronizing PostgreSQL password..."
python scripts/ensure_postgres_password.py

Write-Host "Validating environment..."
python scripts/check_environment.py

Write-Host "Syncing SQLite to PostgreSQL..."
python scripts/sync_sqlite_to_postgres.py

Write-Host "Starting API..."
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000