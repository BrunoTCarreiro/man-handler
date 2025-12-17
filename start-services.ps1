# Home Manual Assistant - Start All Services
# Run this script to start Ollama, Backend, and Frontend
# Usage: .\start-services.ps1 [-Network] or .\start-services.ps1 -n
#   -Network, -n: Expose services to local network (default: localhost only)

param(
    [Parameter()]
    [Alias("n")]
    [switch]$Network
)

# Check if network exposure is requested
$exposeNetwork = $Network

Write-Host "Starting Home Manual Assistant Services..." -ForegroundColor Cyan
if ($exposeNetwork) {
    Write-Host "[INFO] Network exposure enabled - services will be accessible from local network" -ForegroundColor Yellow
} else {
    Write-Host "[INFO] Localhost only - use -Network flag to expose to local network" -ForegroundColor Gray
}
Write-Host ""

# Check if Ollama is running
$ollamaRunning = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollamaRunning) {
    Write-Host "[INFO] Starting Ollama service..." -ForegroundColor Yellow
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 2
    Write-Host "[OK] Ollama started" -ForegroundColor Green
} else {
    Write-Host "[OK] Ollama already running" -ForegroundColor Green
}

Write-Host ""

# Start Backend (FastAPI)
Write-Host "[INFO] Starting Backend API (port 8000)..." -ForegroundColor Yellow
$backendPath = Join-Path $PSScriptRoot "backend"
$hostBinding = if ($exposeNetwork) { "0.0.0.0" } else { "127.0.0.1" }
$exposeNetworkValue = if ($exposeNetwork) { '1' } else { '0' }
$backendCmd = "`$env:EXPOSE_NETWORK='$exposeNetworkValue'; & '$backendPath\.venv\Scripts\python.exe' -m uvicorn backend.main:app --reload --host $hostBinding --port 8000"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; $backendCmd" -WorkingDirectory $PSScriptRoot
Write-Host "[OK] Backend starting in new window" -ForegroundColor Green

Start-Sleep -Seconds 2

# Start Frontend (Vite)
Write-Host "[INFO] Starting Frontend Dev Server (port 5173)..." -ForegroundColor Yellow
$frontendPath = Join-Path $PSScriptRoot "frontend"
$frontendEnv = if ($exposeNetwork) { "VITE_EXPOSE_NETWORK=1" } else { "" }
$frontendCmd = if ($exposeNetwork) { "`$env:VITE_EXPOSE_NETWORK='1'; cd '$frontendPath'; npm run dev" } else { "cd '$frontendPath'; npm run dev" }
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "$frontendCmd" -WorkingDirectory $frontendPath
Write-Host "[OK] Frontend starting in new window" -ForegroundColor Green

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "[OK] All services starting!" -ForegroundColor Green
Write-Host ""
Write-Host "Local access:" -ForegroundColor Yellow
Write-Host "  Backend API:  http://localhost:8000" -ForegroundColor White
Write-Host "  Frontend UI:  http://localhost:5173" -ForegroundColor White
if ($exposeNetwork) {
    Write-Host ""
    Write-Host "Network access (from other devices on your local network):" -ForegroundColor Yellow
    try {
        # Get network IPs, excluding localhost, link-local, and virtual adapters (WSL, Hyper-V, etc.)
        $virtualAdapterKeywords = @('WSL', 'Hyper-V', 'vEthernet', 'VirtualBox', 'VMware', 'Docker', 'WSL2')
        $networkIPs = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
            $ip = $_.IPAddress
            $alias = $_.InterfaceAlias
            $ip -notlike '127.*' -and 
            $ip -notlike '169.254.*' -and
            -not ($virtualAdapterKeywords | Where-Object { $alias -like "*$_*" })
        } | Select-Object IPAddress, InterfaceAlias
        
        if ($networkIPs) {
            foreach ($ipInfo in $networkIPs) {
                Write-Host "  Backend API:  http://$($ipInfo.IPAddress):8000" -ForegroundColor Cyan
                Write-Host "  Frontend UI:  http://$($ipInfo.IPAddress):5173" -ForegroundColor Cyan
            }
        } else {
            Write-Host "  (Run 'ipconfig' to find your local IP address)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  (Run 'ipconfig' to find your local IP address)" -ForegroundColor Gray
    }
}
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop services" -ForegroundColor Gray
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

