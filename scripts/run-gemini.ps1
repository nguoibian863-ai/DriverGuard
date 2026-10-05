param(
    [Parameter(Mandatory=$true)][string]$TaskId,
    [int]$TimeoutSec = 300
)

$ErrorActionPreference = "Stop"

$taskDir    = Join-Path $PSScriptRoot "..\tasks\$TaskId"
$promptPath = Join-Path $taskDir "prompt.md"
$outputPath = Join-Path $taskDir "output.md"
$logPath    = Join-Path $taskDir "gemini.log"

if (-not (Test-Path $promptPath)) {
    Write-Error "Không tìm thấy prompt: $promptPath"
    exit 1
}

$promptContent = Get-Content -Path $promptPath -Raw -Encoding UTF8

try {
    $agy = Join-Path $env:LOCALAPPDATA "agy\bin\agy.exe"
    # Quy tắc của sếp: prompt giao cho Gemini luôn bắt đầu bằng /boost
    $result = & $agy -p "/boost $promptContent" --mode accept-edits --print-timeout "${TimeoutSec}s" 2>&1
} catch {
    $_.Exception.Message | Out-File -FilePath $logPath -Encoding UTF8
    Write-Error "Gemini CLI lỗi khi chạy — xem $logPath"
    exit 1
}

$result | Out-File -FilePath $logPath -Encoding UTF8

$text = $result -join "`n"
if ($text -match "(?s)## OUTPUT_START(.*)## OUTPUT_END") {
    $matches[1].Trim() | Out-File -FilePath $outputPath -Encoding UTF8
} else {
    "> ⚠️ Không tìm thấy marker OUTPUT_START/OUTPUT_END — ghi log gốc.`n`n$text" |
        Out-File -FilePath $outputPath -Encoding UTF8
}

Write-Host "Xong. Kết quả tại: $outputPath"
