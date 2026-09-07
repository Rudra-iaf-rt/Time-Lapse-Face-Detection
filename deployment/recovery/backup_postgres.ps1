# Backup PostgreSQL (PowerShell). Set CONFIRM=yes to allow overwrite.
param(
  [string]$OutDir = "./backups",
  [string]$Confirm = $env:CONFIRM
)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$stamp = Get-Date -Format "yyyyMMddTHHmmssZ"
$out = Join-Path $OutDir "postgres_$stamp.sql"

if ((Test-Path $out) -and $Confirm -ne "yes") {
  Write-Error "Refusing to overwrite $out without CONFIRM=yes"
  exit 1
}

$hostName = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { "localhost" }
$port = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5432" }
$user = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
$db = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "multicam_reid" }

$env:PGPASSWORD = $env:POSTGRES_PASSWORD
pg_dump -h $hostName -p $port -U $user -d $db -F p | Set-Content -Path $out -Encoding utf8
Write-Host "Done: $out"
