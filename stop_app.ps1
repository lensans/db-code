param(
    [int]$Port = 5000
)

$ErrorActionPreference = "Stop"

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if (-not $listeners) {
    Write-Host "No listening process found on port $Port."
    exit 0
}

$killed = $false

foreach ($listener in $listeners) {
    $processId = $listener.OwningProcess
    if (-not $processId) {
        continue
    }

    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if (-not $process) {
        continue
    }

    Write-Host "Stopping process $($process.ProcessName) (PID $processId) on port $Port"
    Stop-Process -Id $processId -Force
    $killed = $true
}

if (-not $killed) {
    Write-Host "No stoppable process found on port $Port."
}
