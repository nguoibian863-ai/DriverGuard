param(
    [Parameter(Mandatory=$true)][string]$TaskId,
    [Parameter(Mandatory=$true)][string]$Status,
    [int]$IncrementFixAttempts = 0
)

$ErrorActionPreference = "Stop"
$statePath = Join-Path $PSScriptRoot "..\state\task-state.json"

$state = if (Test-Path $statePath) {
    Get-Content $statePath -Raw | ConvertFrom-Json
} else {
    [PSCustomObject]@{ tasks = @{} }
}

if (-not $state.tasks.$TaskId) {
    $state.tasks | Add-Member -NotePropertyName $TaskId -NotePropertyValue ([PSCustomObject]@{
        status = $Status
        phase_history = @($Status)
        fix_attempts = 0
        max_fix_attempts = 3
        updated_at = (Get-Date).ToString("o")
    })
} else {
    $state.tasks.$TaskId.status = $Status
    $state.tasks.$TaskId.phase_history += $Status
    $state.tasks.$TaskId.fix_attempts += $IncrementFixAttempts
    $state.tasks.$TaskId.updated_at = (Get-Date).ToString("o")
}

$state | ConvertTo-Json -Depth 10 | Out-File -FilePath $statePath -Encoding UTF8
Write-Host "State cập nhật: $TaskId -> $Status"
