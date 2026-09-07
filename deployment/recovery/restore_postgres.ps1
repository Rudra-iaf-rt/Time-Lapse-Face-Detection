# Restore PostgreSQL (PowerShell). DESTRUCTIVE — requires -Confirm yes
param(
  [Parameter(Mandatory = $true)][string]$DumpFile,
  [string]$Confirm = $env:CONFIRM
)

if ($Confirm -ne "yes") {
  Write-Error "Refusing to restore without CONFIRM=yes"
  exit 1
}

$hostName = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { "localhost" }
$port = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5432" }
$user = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
$db = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "multicam_reid" }

$env:PGPASSWORD = $env:POSTGRES_PASSWORD
psql -h $hostName -p $port -U $user -d $db -f $DumpFile
Write-Host "Restore complete"
