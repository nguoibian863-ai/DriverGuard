param([Parameter(Mandatory=$true)][string]$TaskId)

$taskDir = Join-Path $PSScriptRoot "..\tasks\$TaskId"
$reviewDir = Join-Path $PSScriptRoot "..\reviews"
New-Item -ItemType Directory -Force -Path $reviewDir | Out-Null

# Giả định Claude đã ghi 3 file riêng trước khi gọi script này:
# tasks/<id>/reviewer-output.md, security-output.md, qa-output.md
$reviewer = Get-Content (Join-Path $taskDir "reviewer-output.md") -Raw
$security = Get-Content (Join-Path $taskDir "security-output.md") -Raw
$qa       = Get-Content (Join-Path $taskDir "qa-output.md") -Raw

$merged = @"
# Báo cáo tổng hợp — $TaskId
## Từ Reviewer
$reviewer

## Từ Security Auditor
$security

## Từ QA
$qa
"@

$outPath = Join-Path $reviewDir "$TaskId-$(Get-Date -Format 'yyyyMMdd-HHmmss').md"
$merged | Out-File -FilePath $outPath -Encoding UTF8
Write-Host "Báo cáo tổng hợp: $outPath"
