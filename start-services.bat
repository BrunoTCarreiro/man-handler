@echo off
REM Home Manual Assistant - Start All Services (Batch version)
REM For users who prefer .bat files
REM Usage: start-services.bat [network]
REM   network: Expose services to local network (default: localhost only)
REM
setlocal enabledelayedexpansion

REM Check if network exposure is requested
set "EXPOSE_NETWORK=0"
if /i "%1"=="network" set "EXPOSE_NETWORK=1"
if /i "%1"=="-network" set "EXPOSE_NETWORK=1"
if /i "%1"=="-n" set "EXPOSE_NETWORK=1"

echo.
echo Starting Home Manual Assistant Services...
if "%EXPOSE_NETWORK%"=="1" (
    echo [INFO] Network exposure enabled - services will be accessible from local network
) else (
    echo [INFO] Localhost only - pass "network" parameter to expose to local network
)
echo.

REM Start Ollama (hidden)
echo Starting Ollama service...
start /B ollama serve
timeout /t 2 /nobreak >nul

REM Start Backend
echo Starting Backend API (port 8000)...
if "%EXPOSE_NETWORK%"=="1" (
    set "HOST_BINDING=0.0.0.0"
) else (
    set "HOST_BINDING=127.0.0.1"
)
start "Backend API" cmd /k "cd /d %~dp0 && set EXPOSE_NETWORK=%EXPOSE_NETWORK% && backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host %HOST_BINDING% --port 8000"

timeout /t 2 /nobreak >nul

REM Start Frontend
echo Starting Frontend Dev Server (port 5173)...
if "%EXPOSE_NETWORK%"=="1" (
    start "Frontend Dev" cmd /k "cd /d %~dp0frontend && set VITE_EXPOSE_NETWORK=1 && npm run dev"
) else (
    start "Frontend Dev" cmd /k "cd /d %~dp0frontend && npm run dev"
)

echo.
echo ========================================
echo All services starting!
echo.
echo Local access:
echo   Backend API:  http://localhost:8000
echo   Frontend UI:  http://localhost:5173
if "%EXPOSE_NETWORK%"=="1" (
    echo.
    echo Network access (from other devices on your local network):
    echo   Run 'ipconfig' to find your local IP address
    echo   Then use: http://YOUR_IP:8000 (Backend) and http://YOUR_IP:5173 (Frontend)
)
echo.
echo Close the terminal windows to stop services
echo ========================================
echo.

