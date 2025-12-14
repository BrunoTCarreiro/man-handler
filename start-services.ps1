# Home Manual Assistant - Start All Services
# Run this script to start Ollama, Backend, and Frontend

Write-Host "Starting Home Manual Assistant Services..." -ForegroundColor Cyan
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
$backendCmd = "& '$backendPath\.venv\Scripts\python.exe' -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; $backendCmd" -WorkingDirectory $PSScriptRoot
Write-Host "[OK] Backend starting in new window" -ForegroundColor Green

Start-Sleep -Seconds 2

# Start Frontend (Vite)
Write-Host "[INFO] Starting Frontend Dev Server (port 5173)..." -ForegroundColor Yellow
$frontendPath = Join-Path $PSScriptRoot "frontend"
$frontendCmd = "cd '$frontendPath'; npm run dev"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "$frontendCmd" -WorkingDirectory $frontendPath
Write-Host "[OK] Frontend starting in new window" -ForegroundColor Green

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "[OK] All services starting!" -ForegroundColor Green
Write-Host ""
Write-Host "Backend API:  http://localhost:8000" -ForegroundColor White
Write-Host "Frontend UI:  http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop services" -ForegroundColor Gray
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

