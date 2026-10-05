# Chạy dashboard Next.js (cổng 3000). Cần backend đang chạy ở cổng 8000.
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location (Join-Path $root "apps\web")
npm run dev
