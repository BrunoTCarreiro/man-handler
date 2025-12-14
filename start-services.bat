@echo off
REM Home Manual Assistant - Start All Services (Batch version)
REM For users who prefer .bat files

echo.
echo Starting Home Manual Assistant Services...
echo.

REM Start Ollama (hidden)
echo Starting Ollama service...
start /B ollama serve
timeout /t 2 /nobreak >nul

REM Start Backend
echo Starting Backend API (port 8000)...
start "Backend API" cmd /k "cd /d %~dp0 && backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 2 /nobreak >nul

REM Start Frontend
echo Starting Frontend Dev Server (port 5173)...
start "Frontend Dev" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo All services starting!
echo.
echo Backend API:  http://localhost:8000
echo Frontend UI:  http://localhost:5173
echo.
echo Close the terminal windows to stop services
echo ========================================
echo.

