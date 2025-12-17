# Restart Backend Service
# This script restarts the backend API server

param(
    [switch]$Network
)

$scriptRoot = $PSScriptRoot
$backendPath = Join-Path $scriptRoot "backend"

Write-Host "Restarting Backend API..." -ForegroundColor Yellow

# Try to find and stop existing backend process
# Look for processes listening on port 8000 (backend port)
try {
    $port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($port8000) {
        $pid = $port8000.OwningProcess
        Write-Host "[INFO] Found process on port 8000 (PID: $pid), stopping..." -ForegroundColor Gray
        try {
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Host "[OK] Stopped backend process (PID: $pid)" -ForegroundColor Green
            Start-Sleep -Seconds 2
        } catch {
            Write-Host "[WARN] Could not stop process $pid, it may have already stopped" -ForegroundColor Yellow
        }
    }
} catch {
    # If Get-NetTCPConnection fails, try alternative method
    Write-Host "[INFO] Checking for backend processes..." -ForegroundColor Gray
    $pythonProcs = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -like "*uvicorn*" -or $_.Path -like "*backend*"
    }
    if ($pythonProcs) {
        foreach ($proc in $pythonProcs) {
            try {
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                Write-Host "[OK] Stopped process $($proc.Id)" -ForegroundColor Green
            } catch {
                Write-Host "[WARN] Could not stop process $($proc.Id)" -ForegroundColor Yellow
            }
        }
        Start-Sleep -Seconds 2
    }
}

# Determine host binding
$hostBinding = if ($Network) { "0.0.0.0" } else { "127.0.0.1" }
$exposeNetworkValue = if ($Network) { '1' } else { '0' }

# Start backend
Write-Host "[INFO] Starting Backend API (port 8000)..." -ForegroundColor Yellow
$backendCmd = "`$env:EXPOSE_NETWORK='$exposeNetworkValue'; & '$backendPath\.venv\Scripts\python.exe' -m uvicorn backend.main:app --reload --host $hostBinding --port 8000"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$scriptRoot'; $backendCmd" -WorkingDirectory $scriptRoot

Write-Host "[OK] Backend restarted in new window" -ForegroundColor Green
Write-Host ""
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
if ($Network) {
    Write-Host "Network access enabled" -ForegroundColor Cyan
}

