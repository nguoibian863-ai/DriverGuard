param([int]$TimeoutSec = 300)

Write-Host "== Lint =="
npm run lint

Write-Host "== Build =="
npm run build

Write-Host "== Test =="
npm test -- --ci
