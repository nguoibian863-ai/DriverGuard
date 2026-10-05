# Chạy backend DriverGuard (kèm AI worker). Dùng: .\scripts\run_backend.ps1 [-Simulate]
param([switch]$Simulate, [int]$Port = 8000)

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = $root.Path
$env:DRIVERGUARD_SIMULATE = if ($Simulate) { "1" } else { "0" }
if (-not $env:DRIVERGUARD_DB) { $env:DRIVERGUARD_DB = Join-Path $root "data\driverguard.db" }

Set-Location (Join-Path $root "apps\backend")
& (Join-Path $root ".venv\Scripts\python.exe") -m uvicorn app.main:app --host 127.0.0.1 --port $Port
